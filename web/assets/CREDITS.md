# 에셋 출처 및 라이선스

이 디렉터리의 모든 이미지는 **Kenney** (https://kenney.nl) 제작이며 **CC0 1.0 (Public Domain Dedication)** 으로 배포됩니다.

> License: Creative Commons Zero, CC0
> https://creativecommons.org/publicdomain/zero/1.0/
>
> This content is free to use in personal, educational and commercial projects.
> Support us by crediting Kenney or www.kenney.nl (this is not mandatory)

CC0는 **저작자 표시 의무가 없지만**, 제작자의 요청에 따라 자발적으로 표기합니다.

## 사용한 팩

| 디렉터리 | 팩 | 원본 개수 | 사용 | 출처 |
|---|---|---|---|---|
| `characters/` | Shape Characters (1.0) | 100 | 104 파일 | https://kenney.nl/assets/shape-characters |
| `library/` | Isometric Miniature Library (2.1) | 35 | 88 파일 | https://kenney.nl/assets/isometric-miniature-library |
| `floor/` | Isometric Miniature Prototype | 60 | 28 파일 | https://kenney.nl/assets/isometric-miniature-prototype |
| `walls/` | Isometric Miniature Prototype | 60 | 7종 × 3색 = 21 파일 (**색 변경**) | 위와 같음 |

## 색을 바꾼 에셋 — `walls/`

Prototype 팩은 배치 확인용이라 모든 오브젝트가 주황(`#ed8b1c`)이다. 그대로 쓰면 Library 팩의
나무·돌 색과 섞이지 않는다. 그런데 **코너 조각(`wallCorner`)이 이 팩에만 있다** — Library 팩의
벽은 `wallBooks`·`wallDoorway` 둘뿐이고 모서리를 맞출 조각이 없어 두 벽이 서로를 뚫고 나온다.

그래서 `wall`·`wallCorner`·`window`·`doorway` 7종을 가져와 **채도만 낮추고 명암은 보존**해
세 가지 벽 색(`gray`·`beige`·`cream`)을 만들었다. CC0는 수정과 재배포에 제약이 없다.

재현: `python tools/리컬러.py <팩을 푼 Isometric 폴더>`

## 규격

- **characters** — 80×80px 몸통, 부품 조립식 (몸통 + 얼굴 + 손)
- **library / floor** — 256×512px, 4방향(`_N` `_E` `_W` `_S`), 정투영(Isometric) 버전

## 검토했으나 채택하지 않은 것

| 팩 | 사유 |
|---|---|
| Kenney Toon Characters | 측면 뷰 플랫포머용 — 아이소메트릭 부적합 |
| Kenney Robot Pack | 측면·상단 뷰만 제공, 4방향 없음 |
| Kenney Animal Pack | 정면 단일 방향 — 이동 방향 표현 불가 |
| Kenney Mini/Blocky Characters | 3D 모델(.obj/.glb) — 스프라이트 렌더링 공정 필요 |
| itch.io 8-Directional Character Pack | 유료 ($5) |
| OpenGameArt 아이소메트릭 캐릭터 | 판타지 테마 — 연구소 컨셉과 불일치 |
