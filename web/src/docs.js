// 문서 이름 한국어 표기 — 서고의 52건은 영문 위키백과다.
// 화면에서 "Assortative mating 읽는 중"이라고 뜨면 무슨 말인지 알 수 없다.
// **인용·대조는 여전히 원제로 한다.** 이 표는 화면에 보여 줄 때만 쓴다.
export const DOC_KO = {
  // 유형론
  "Analytical psychology": "분석심리학",
  "Carl Jung": "카를 융",
  "Collective unconscious": "집단 무의식",
  "Enneagram of Personality": "에니어그램",
  "Extraversion and introversion": "외향성과 내향성",
  "Jungian archetypes": "융의 원형",
  "Keirsey Temperament Sorter": "키어시 기질 분류",
  "Myers–Briggs Type Indicator": "MBTI 검사",
  "Psychological Types": "융 『심리 유형』",
  "Socionics": "소시오닉스",
  "Temperament": "기질",
  // 성격심리
  "16PF Questionnaire": "16PF 성격 검사",
  "Big Five personality traits": "빅 파이브 성격 특성",
  "Gordon Allport": "고든 올포트",
  "HEXACO model of personality structure": "HEXACO 성격 모형",
  "Hans Eysenck": "한스 아이젱크",
  "Personality": "성격",
  "Personality psychology": "성격심리학",
  "Personality type": "성격 유형",
  "Person–situation debate": "사람·상황 논쟁",
  "Raymond Cattell": "레이먼드 카텔",
  "Trait theory": "특성 이론",
  // 측정
  "Construct validity": "구성 타당도",
  "Effect size": "효과 크기",
  "Factor analysis": "요인 분석",
  "Personality test": "성격 검사",
  "Psychometrics": "심리 측정학",
  "Questionnaire": "설문지",
  "Reliability (statistics)": "신뢰도",
  "Replication crisis": "재현성 위기",
  "Statistical significance": "통계적 유의성",
  "Test validity": "검사 타당도",
  "Validity (statistics)": "타당도",
  // 유사사례
  "Astrology": "점성술",
  "Blood type personality theory": "혈액형 성격설",
  "Falsifiability": "반증 가능성",
  "Graphology": "필적학",
  "Phrenology": "골상학",
  "Pseudoscience": "유사과학",
  "Scientific consensus": "과학적 합의",
  // 관계
  "Assortative mating": "끼리끼리 짝짓기",
  "Industrial and organizational psychology": "산업조직심리학",
  "Interpersonal attraction": "대인 매력",
  "Interpersonal compatibility": "대인 궁합",
  "Interpersonal relationship": "대인 관계",
  "Social psychology": "사회심리학",
  // 편향
  "Barnum effect": "바넘 효과",
  "Cognitive bias": "인지 편향",
  "Confirmation bias": "확증 편향",
  "Halo effect": "후광 효과",
  "Self-fulfilling prophecy": "자기충족 예언",
  "Stereotype": "고정관념",
};

/** 한국어 이름. 표에 없으면 원제 그대로 (코퍼스를 갈아 끼워도 깨지지 않는다) */
export const docKo = (title) => DOC_KO[title] || title;
