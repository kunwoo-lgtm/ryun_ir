// 륜 게런티 함수 — 수기 메모(2026-07-22) 원본 공식의 구현
//
//   Ⅰ. 기본 지출 항목
//      P(부산) = 10만원 × m  + m·α   (m  = 부산 아티스트 수)
//      S(서울) = 20만원 × m′ + m′·α  (m′ = 서울 아티스트 수)
//      P + S = 기본 지출 합계
//
//   Ⅱ. α (러닝 게런티)
//      α = 2만원 × n″ ÷ (m + m′)    (n″ = 티케팅 수)
//      → 티켓 1장당 2만원이 전체 아티스트에게 균등 분배된다.
//
//   Ⅲ. 음원 판매 수익
//      별도 수익 풀. 러닝 게런티와 같은 방식(균등 분배)으로 나눈다.

const MAN = 10_000; // 만원 단위

export const DEFAULT_PARAMS = {
  baseBusan: 10 * MAN,   // 부산 아티스트 기본 게런티
  baseSeoul: 20 * MAN,   // 서울 아티스트 기본 게런티
  perTicket: 2 * MAN,    // 티켓 1장당 러닝 게런티 재원
};

/**
 * 게런티 함수
 * @param m       부산 아티스트 수
 * @param mPrime  서울 아티스트 수
 * @param tickets 티케팅 수 (n″)
 * @param music   음원 판매 수익 (Ⅲ, 선택)
 */
export function guarantee(m, mPrime, tickets, music = 0, params = DEFAULT_PARAMS) {
  const n = m + mPrime;
  const alpha = Math.floor((params.perTicket * tickets) / n); // Ⅱ
  const musicShare = Math.floor(music / n);                   // Ⅲ (균등 분배)

  const busanPerArtist = params.baseBusan + alpha + musicShare;
  const seoulPerArtist = params.baseSeoul + alpha + musicShare;

  const P = params.baseBusan * m + alpha * m;   // Ⅰ P(부산)
  const S = params.baseSeoul * mPrime + alpha * mPrime; // Ⅰ S(서울)

  return {
    alpha, musicShare,
    busanPerArtist, seoulPerArtist,
    P, S,
    total: P + S + musicShare * n, // 기본 지출 합계 + 음원 분배
  };
}

// ------------------------------------------------------------------
// 예시: node contracts/ryun-guarantee-function.mjs
// ------------------------------------------------------------------
if (import.meta.url === `file://${process.argv[1]}`) {
  const man = (v) => (v / MAN).toLocaleString("ko-KR", { maximumFractionDigits: 2 }) + "만원";
  console.log("륜 게런티 함수 — 부산 5인(기본 10만원) · 서울 2인(기본 20만원), 티켓당 2만원\n");
  for (const [tickets, music] of [[0, 0], [100, 0], [300, 0], [300, 70 * MAN]]) {
    const r = guarantee(5, 2, tickets, music);
    console.log(`티켓 ${tickets}장${music ? `, 음원 수익 ${man(music)}` : ""}`);
    console.log(`  α(러닝 게런티) = 2만원 × ${tickets} ÷ 7 = ${man(r.alpha)}` +
                (music ? ` | 음원 분배 = ${man(r.musicShare)}/인` : ""));
    console.log(`  부산 아티스트 1인: ${man(r.busanPerArtist)} | 서울 아티스트 1인: ${man(r.seoulPerArtist)}`);
    console.log(`  P(부산) ${man(r.P)} + S(서울) ${man(r.S)} → 총 지출 ${man(r.total)}\n`);
  }
}
