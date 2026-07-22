// 게런티 함수 기반 수익배분 — 레퍼런스 구현 (오프체인 검증/시뮬레이션용)
// Solidity 컨트랙트(RyunGuaranteeDistribution.sol)와 동일한 규칙을 따른다.
//
//   1단계: 누적 미지급 게런티(arrears) 우선 상환 (비례 배분)
//   2단계: 당회차 게런티 지급, 예산 부족분은 arrears 로 누적
//   3단계: 초과 수익을 가중치(N값)에 비례해 배분

export function createLedger(partners, { feeBps = 0 } = {}) {
  // partners: [{ id, guarantee, weight }]
  return {
    feeBps,
    round: 0,
    partners: partners.map((p) => ({ ...p, arrears: 0, paidTotal: 0 })),
    history: [],
  };
}

// 게런티 함수: 회차 수익(revenue)을 규칙에 따라 배분한 결과를 반환
export function settle(ledger, revenue) {
  ledger.round += 1;
  const fee = Math.floor((revenue * ledger.feeBps) / 10_000);
  let budget = revenue - fee;
  const record = { round: ledger.round, revenue, fee, payouts: {} };
  const pay = (p, amount, kind) => {
    p.paidTotal += amount;
    const r = (record.payouts[p.id] ??= { arrears: 0, guarantee: 0, surplus: 0 });
    r[kind] += amount;
  };

  // --- 1단계: 누적 미지급 게런티 우선 상환 ---
  const totalArrears = ledger.partners.reduce((s, p) => s + p.arrears, 0);
  if (totalArrears > 0) {
    const pool = Math.min(budget, totalArrears);
    let paidSum = 0;
    ledger.partners.forEach((p, i) => {
      if (p.arrears === 0) return;
      let amt = Math.floor((pool * p.arrears) / totalArrears);
      if (i === ledger.partners.length - 1) amt = Math.min(pool - paidSum, p.arrears);
      amt = Math.min(amt, p.arrears);
      p.arrears -= amt;
      paidSum += amt;
      pay(p, amt, "arrears");
    });
    budget -= paidSum;
  }

  // --- 2단계: 당회차 게런티 (부족분 누적) ---
  const totalGuarantee = ledger.partners.reduce((s, p) => s + p.guarantee, 0);
  if (budget > 0 && totalGuarantee > 0) {
    const pool = Math.min(budget, totalGuarantee);
    let paidSum = 0;
    ledger.partners.forEach((p) => {
      let amt = Math.min(Math.floor((pool * p.guarantee) / totalGuarantee), p.guarantee);
      const shortfall = p.guarantee - amt;
      if (shortfall > 0) p.arrears += shortfall;
      paidSum += amt;
      pay(p, amt, "guarantee");
    });
    budget -= paidSum;
  } else if (budget === 0 && totalGuarantee > 0) {
    ledger.partners.forEach((p) => (p.arrears += p.guarantee));
  }

  // --- 3단계: 초과 수익을 가중치(N값)로 배분 ---
  const totalWeight = ledger.partners.reduce((s, p) => s + p.weight, 0);
  if (budget > 0 && totalWeight > 0) {
    const surplus = budget;
    let distributed = 0;
    ledger.partners.forEach((p, i) => {
      let amt = Math.floor((surplus * p.weight) / totalWeight);
      if (i === ledger.partners.length - 1) amt = surplus - distributed;
      distributed += amt;
      pay(p, amt, "surplus");
    });
    budget = 0;
  }

  ledger.history.push(record);
  return record;
}

// ------------------------------------------------------------------
// 시뮬레이션: node contracts/guarantee-distribution.mjs
// ------------------------------------------------------------------
if (import.meta.url === `file://${process.argv[1]}`) {
  const won = (n) => n.toLocaleString("ko-KR") + "원";
  const ledger = createLedger(
    [
      { id: "아티스트A", guarantee: 500_000, weight: 3 },
      { id: "아티스트B", guarantee: 300_000, weight: 2 },
      { id: "기획/운영",  guarantee: 200_000, weight: 5 },
    ],
    { feeBps: 300 } // 플랫폼 수수료 3% (독점 플랫폼 대비 저율)
  );

  console.log("게런티 함수 시뮬레이션 — 파트너 3인, 수수료 3%\n");
  for (const [label, revenue] of [
    ["회차 1: 예산 부족 (소규모 지원사업)", 600_000],
    ["회차 2: 게런티 충족 + 소액 초과", 1_300_000],
    ["회차 3: 유통 확대 (매출 성장)", 3_000_000],
  ]) {
    const rec = settle(ledger, revenue);
    console.log(`${label} — 수익 ${won(revenue)}, 수수료 ${won(rec.fee)}`);
    for (const p of ledger.partners) {
      const r = rec.payouts[p.id] ?? { arrears: 0, guarantee: 0, surplus: 0 };
      console.log(
        `  ${p.id}: 미지급상환 ${won(r.arrears)} + 게런티 ${won(r.guarantee)} + 초과분배 ${won(r.surplus)}` +
        `  (잔여 미지급 ${won(p.arrears)})`
      );
    }
    console.log();
  }
  console.log("누적 수령액:");
  for (const p of ledger.partners) console.log(`  ${p.id}: ${won(p.paidTotal)}`);
}
