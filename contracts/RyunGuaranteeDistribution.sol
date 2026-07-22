// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * RyunGuaranteeDistribution — 게런티 함수 기반 수익배분 컨트랙트
 *
 * 배경 (음성 메모 요지):
 *  - 기존 하청 구조를 파트너 간 수익 분배 공식으로 전환한다.
 *  - 아티스트는 예산이 적은 회차에 게런티(최소 보장금)를 전부 받지 못할 수 있다.
 *    이때 미지급분은 사라지지 않고 체인 위에 누적되어 다음 회차에 최우선 정산된다.
 *  - 분배 규칙이 함수로 공개되어 있으므로("눈에 보이니까") 분쟁 여지가 없고,
 *    조정은 오직 파라미터(가중치 N값, 수수료율)로만 이루어진다.
 *  - 독점 티켓팅 플랫폼의 고율 수수료에 대한 대안으로 플랫폼 수수료는
 *    낮은 상한(MAX_FEE_BPS) 안에서만 설정할 수 있다.
 *
 * 게런티 함수 정의 (회차 정산, 순수익 B):
 *  1단계 — 누적 미지급 게런티(arrears) 우선 상환.
 *          B < ΣA 이면 A_i 비례 배분 후 종료, 잔여 미지급분은 계속 누적.
 *  2단계 — 당회차 게런티 지급. 잔여 예산 B1 < ΣG 이면 G_i 비례 배분하고
 *          부족분을 arrears 에 누적.
 *  3단계 — 초과 수익 S = B1 - ΣG 를 가중치 w_i(N값)에 비례해 배분.
 *
 * 지급은 pull-payment 방식: 정산은 잔고(credit)만 기록하고,
 * 파트너가 withdraw() 로 직접 인출한다.
 */
contract RyunGuaranteeDistribution {
    // ---------------------------------------------------------------
    // 상태
    // ---------------------------------------------------------------

    struct Partner {
        uint256 guarantee;   // G_i: 회차당 최소 보장금 (wei)
        uint256 weight;      // w_i: 초과 수익 분배 가중치 (N값)
        uint256 arrears;     // A_i: 누적 미지급 게런티
        bool active;
    }

    address public owner;
    address public feeRecipient;

    /// 플랫폼 수수료율 (basis points). 독점 플랫폼 대비 낮은 상한을 강제한다.
    uint16 public feeBps;
    uint16 public constant MAX_FEE_BPS = 500; // 5%

    address[] public partnerList;
    mapping(address => Partner) public partners;

    /// 인출 가능 잔고 (pull-payment)
    mapping(address => uint256) public credit;

    uint256 public round; // 정산 회차 번호

    // ---------------------------------------------------------------
    // 이벤트 — 모든 정산 내역이 체인에 공개 기록된다
    // ---------------------------------------------------------------

    event PartnerSet(address indexed partner, uint256 guarantee, uint256 weight);
    event PartnerDeactivated(address indexed partner);
    event RevenueSettled(uint256 indexed round, uint256 gross, uint256 fee, uint256 net);
    event ArrearsPaid(uint256 indexed round, address indexed partner, uint256 amount, uint256 remainingArrears);
    event GuaranteePaid(uint256 indexed round, address indexed partner, uint256 amount, uint256 shortfallAccrued);
    event SurplusPaid(uint256 indexed round, address indexed partner, uint256 amount);
    event Withdrawn(address indexed partner, uint256 amount);
    event FeeUpdated(uint16 feeBps);

    // ---------------------------------------------------------------

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    bool private _locked;
    modifier nonReentrant() {
        require(!_locked, "reentrant");
        _locked = true;
        _;
        _locked = false;
    }

    constructor(address _feeRecipient, uint16 _feeBps) {
        require(_feeBps <= MAX_FEE_BPS, "fee too high");
        owner = msg.sender;
        feeRecipient = _feeRecipient;
        feeBps = _feeBps;
    }

    // ---------------------------------------------------------------
    // 파트너 관리 — 분배 규칙 조정은 파라미터 변경으로만 가능
    // ---------------------------------------------------------------

    function setPartner(address account, uint256 guarantee, uint256 weight) external onlyOwner {
        require(account != address(0), "zero address");
        Partner storage p = partners[account];
        if (!p.active) {
            partnerList.push(account);
            p.active = true;
        }
        p.guarantee = guarantee;
        p.weight = weight;
        emit PartnerSet(account, guarantee, weight);
    }

    /// 비활성화해도 누적 미지급분(arrears)과 잔고는 보존된다.
    function deactivatePartner(address account) external onlyOwner {
        require(partners[account].active, "not active");
        partners[account].active = false;
        emit PartnerDeactivated(account);
    }

    function setFee(uint16 _feeBps) external onlyOwner {
        require(_feeBps <= MAX_FEE_BPS, "fee too high");
        feeBps = _feeBps;
        emit FeeUpdated(_feeBps);
    }

    // ---------------------------------------------------------------
    // 게런티 함수 — 수익 입금과 동시에 회차 정산
    // ---------------------------------------------------------------

    receive() external payable {
        settle();
    }

    function settle() public payable nonReentrant {
        require(msg.value > 0, "no revenue");
        round += 1;

        uint256 fee = (msg.value * feeBps) / 10_000;
        uint256 budget = msg.value - fee;
        if (fee > 0) credit[feeRecipient] += fee;
        emit RevenueSettled(round, msg.value, fee, budget);

        // --- 1단계: 누적 미지급 게런티 우선 상환 ---
        uint256 totalArrears = 0;
        uint256 n = partnerList.length;
        for (uint256 i = 0; i < n; i++) {
            totalArrears += partners[partnerList[i]].arrears;
        }
        if (totalArrears > 0) {
            uint256 pool = budget >= totalArrears ? totalArrears : budget;
            uint256 paidSum = 0;
            for (uint256 i = 0; i < n; i++) {
                Partner storage p = partners[partnerList[i]];
                if (p.arrears == 0) continue;
                uint256 pay = (pool * p.arrears) / totalArrears;
                // 마지막 파트너가 반올림 잔여분을 흡수
                if (i == n - 1 && pool > paidSum) pay = pool - paidSum;
                if (pay > p.arrears) pay = p.arrears;
                p.arrears -= pay;
                credit[partnerList[i]] += pay;
                paidSum += pay;
                emit ArrearsPaid(round, partnerList[i], pay, p.arrears);
            }
            budget -= paidSum;
            if (budget == 0) {
                // 예산이 미지급 상환으로 소진되어도 당회차 게런티는 부채로 누적된다
                for (uint256 i = 0; i < n; i++) {
                    Partner storage p = partners[partnerList[i]];
                    if (p.active && p.guarantee > 0) {
                        p.arrears += p.guarantee;
                        emit GuaranteePaid(round, partnerList[i], 0, p.guarantee);
                    }
                }
                return;
            }
        }

        // --- 2단계: 당회차 게런티 지급 (부족분은 누적) ---
        uint256 totalGuarantee = 0;
        for (uint256 i = 0; i < n; i++) {
            Partner storage p = partners[partnerList[i]];
            if (p.active) totalGuarantee += p.guarantee;
        }
        if (totalGuarantee > 0) {
            uint256 pool = budget >= totalGuarantee ? totalGuarantee : budget;
            uint256 paidSum = 0;
            for (uint256 i = 0; i < n; i++) {
                Partner storage p = partners[partnerList[i]];
                if (!p.active || p.guarantee == 0) continue;
                uint256 pay = (pool * p.guarantee) / totalGuarantee;
                if (pay > p.guarantee) pay = p.guarantee;
                uint256 shortfall = p.guarantee - pay;
                if (shortfall > 0) p.arrears += shortfall;
                credit[partnerList[i]] += pay;
                paidSum += pay;
                emit GuaranteePaid(round, partnerList[i], pay, shortfall);
            }
            budget -= paidSum;
            if (budget == 0) return;
        }

        // --- 3단계: 초과 수익을 가중치(N값)에 비례해 배분 ---
        uint256 totalWeight = 0;
        for (uint256 i = 0; i < n; i++) {
            Partner storage p = partners[partnerList[i]];
            if (p.active) totalWeight += p.weight;
        }
        if (totalWeight == 0) {
            // 분배 대상이 없으면 잔여분은 수수료 수취인에게
            credit[feeRecipient] += budget;
            return;
        }
        uint256 surplus = budget;
        uint256 distributed = 0;
        uint256 lastActive = 0;
        for (uint256 i = 0; i < n; i++) {
            if (partners[partnerList[i]].active) lastActive = i;
        }
        for (uint256 i = 0; i < n; i++) {
            Partner storage p = partners[partnerList[i]];
            if (!p.active || p.weight == 0) continue;
            uint256 pay = (surplus * p.weight) / totalWeight;
            if (i == lastActive) pay = surplus - distributed; // 반올림 잔여분 흡수
            credit[partnerList[i]] += pay;
            distributed += pay;
            emit SurplusPaid(round, partnerList[i], pay);
        }
    }

    // ---------------------------------------------------------------
    // 인출
    // ---------------------------------------------------------------

    function withdraw() external nonReentrant {
        uint256 amount = credit[msg.sender];
        require(amount > 0, "nothing to withdraw");
        credit[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        emit Withdrawn(msg.sender, amount);
    }

    // ---------------------------------------------------------------
    // 조회 — 누구나 분배 상태를 검증할 수 있다
    // ---------------------------------------------------------------

    function partnerCount() external view returns (uint256) {
        return partnerList.length;
    }

    function partnerInfo(address account)
        external
        view
        returns (uint256 guarantee, uint256 weight, uint256 arrears, uint256 balance, bool active)
    {
        Partner storage p = partners[account];
        return (p.guarantee, p.weight, p.arrears, credit[account], p.active);
    }
}
