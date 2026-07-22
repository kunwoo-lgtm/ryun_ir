// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * RyunArtistGuarantee — 수기 메모(2026-07-22) 게런티 함수의 온체인 구현
 *
 *  Ⅰ. 기본 지출 항목
 *     P(부산) = baseBusan × m  + m·α     (m  = 부산 아티스트 수)
 *     S(서울) = baseSeoul × m′ + m′·α    (m′ = 서울 아티스트 수)
 *
 *  Ⅱ. 러닝 게런티
 *     α = perTicket × n″ ÷ (m + m′)     (n″ = 티케팅 수)
 *     티켓 1장당 perTicket 이 전체 아티스트에게 균등 분배된다.
 *
 *  Ⅲ. 음원 판매 수익
 *     정산 시 함께 입금된 별도 풀. 러닝 게런티와 같은 방식으로 균등 분배.
 *
 *  기본값: baseBusan 10만원, baseSeoul 20만원, perTicket 2만원 상당액.
 *  금액 단위는 배포 시 지정하는 KRW 스테이블 단위(wei 환산)로 표현한다.
 */
contract RyunArtistGuarantee {
    enum Region { Busan, Seoul }

    address public owner;

    uint256 public baseBusan;  // 부산 기본 게런티
    uint256 public baseSeoul;  // 서울 기본 게런티
    uint256 public perTicket;  // 티켓 1장당 러닝 게런티 재원

    address[] public artistList;
    mapping(address => Region) public regionOf;
    mapping(address => bool) public isArtist;
    mapping(address => uint256) public credit; // pull-payment 잔고

    uint256 public round;

    event ArtistAdded(address indexed artist, Region region);
    event ArtistRemoved(address indexed artist);
    event EventSettled(
        uint256 indexed round,
        uint256 tickets,
        uint256 alpha,
        uint256 musicPool,
        uint256 musicShare,
        uint256 totalPaid
    );
    event Credited(uint256 indexed round, address indexed artist, uint256 base, uint256 alpha, uint256 musicShare);
    event Withdrawn(address indexed artist, uint256 amount);

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

    constructor(uint256 _baseBusan, uint256 _baseSeoul, uint256 _perTicket) {
        owner = msg.sender;
        baseBusan = _baseBusan;   // 예: 10만원 상당
        baseSeoul = _baseSeoul;   // 예: 20만원 상당
        perTicket = _perTicket;   // 예: 2만원 상당
    }

    // ------------------------------------------------------------
    // 아티스트 관리
    // ------------------------------------------------------------

    function addArtist(address artist, Region region) external onlyOwner {
        require(artist != address(0), "zero address");
        require(!isArtist[artist], "already added");
        isArtist[artist] = true;
        regionOf[artist] = region;
        artistList.push(artist);
        emit ArtistAdded(artist, region);
    }

    function removeArtist(address artist) external onlyOwner {
        require(isArtist[artist], "not artist");
        isArtist[artist] = false;
        for (uint256 i = 0; i < artistList.length; i++) {
            if (artistList[i] == artist) {
                artistList[i] = artistList[artistList.length - 1];
                artistList.pop();
                break;
            }
        }
        emit ArtistRemoved(artist);
    }

    function setParams(uint256 _baseBusan, uint256 _baseSeoul, uint256 _perTicket) external onlyOwner {
        baseBusan = _baseBusan;
        baseSeoul = _baseSeoul;
        perTicket = _perTicket;
    }

    // ------------------------------------------------------------
    // 게런티 함수 실행 — 공연 1회 정산
    // ------------------------------------------------------------

    /// 필요 입금액 미리보기: 기본 게런티 합계 + 티켓 러닝 게런티 (음원 풀 제외)
    function requiredDeposit(uint256 tickets) public view returns (uint256 total) {
        uint256 n = artistList.length;
        require(n > 0, "no artists");
        for (uint256 i = 0; i < n; i++) {
            total += regionOf[artistList[i]] == Region.Busan ? baseBusan : baseSeoul;
        }
        total += perTicket * tickets;
    }

    /**
     * 공연 정산. msg.value = 기본 게런티 합계 + perTicket×tickets + 음원 판매 수익(선택).
     * 초과분은 전액 Ⅲ(음원 판매 수익) 풀로 간주되어 균등 분배된다.
     */
    function settleEvent(uint256 tickets) external payable onlyOwner nonReentrant {
        uint256 n = artistList.length;
        require(n > 0, "no artists");

        uint256 required = requiredDeposit(tickets);
        require(msg.value >= required, "insufficient deposit");

        round += 1;

        uint256 alpha = (perTicket * tickets) / n;      // Ⅱ 러닝 게런티
        uint256 musicPool = msg.value - required;       // Ⅲ 음원 판매 수익
        uint256 musicShare = musicPool / n;

        uint256 totalPaid = 0;
        for (uint256 i = 0; i < n; i++) {
            address a = artistList[i];
            uint256 base = regionOf[a] == Region.Busan ? baseBusan : baseSeoul;
            uint256 amount = base + alpha + musicShare;
            credit[a] += amount;
            totalPaid += amount;
            emit Credited(round, a, base, alpha, musicShare);
        }

        // 정수 나눗셈 잔여분은 주최측(owner) 잔고로
        if (msg.value > totalPaid) credit[owner] += msg.value - totalPaid;

        emit EventSettled(round, tickets, alpha, musicPool, musicShare, totalPaid);
    }

    // ------------------------------------------------------------
    // 인출 / 조회
    // ------------------------------------------------------------

    function withdraw() external nonReentrant {
        uint256 amount = credit[msg.sender];
        require(amount > 0, "nothing to withdraw");
        credit[msg.sender] = 0;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        emit Withdrawn(msg.sender, amount);
    }

    function artistCount() external view returns (uint256) {
        return artistList.length;
    }

    /// 게런티 함수 미리보기: 티켓 수·음원 풀 기준 1인 수령액
    function preview(uint256 tickets, uint256 musicPool)
        external
        view
        returns (uint256 alpha, uint256 musicShare, uint256 busanPerArtist, uint256 seoulPerArtist)
    {
        uint256 n = artistList.length;
        require(n > 0, "no artists");
        alpha = (perTicket * tickets) / n;
        musicShare = musicPool / n;
        busanPerArtist = baseBusan + alpha + musicShare;
        seoulPerArtist = baseSeoul + alpha + musicShare;
    }
}
