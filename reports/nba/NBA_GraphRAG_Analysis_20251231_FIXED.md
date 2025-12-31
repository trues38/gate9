# 🏀 NBA Graph RAG 분석 보고서 (수정판)

**생성일시**: 2025-12-31 10:00
**분석 대상**: 2025년 12월 31일 (4경기)
**분석 방법**: Graph RAG + PLAYS_FOR 관계 기반
**데이터 출처**: Neo4j Graph Database (VPS)
**수정사항**: Player-[:PLAYS_FOR]->Team 관계 우선 사용

---

## 📅 경기 일정 (한국시간)

| 시간 | 원정 | 홈 | 비고 |
|------|------|-----|------|
| 10:00 | Philadelphia 76ers | Memphis Grizzlies |  |
| 11:00 | Boston Celtics | Utah Jazz | 🔥 강팀 |
| 12:30 | Detroit Pistons | Los Angeles Lakers | ⚠️ 약팀 |
| 13:00 | Sacramento Kings | Los Angeles Clippers | 🔥 강팀 |

---

## 🎯 경기 1: Philadelphia 76ers @ Memphis Grizzlies

**PHI**: 2승 3패 (40.0%) | 
**MEM**: 2승 3패 (40.0%)

**PHI 주요선수:**
- Tyrese Maxey: 27.2p 2.6r 5.6a
- VJ Edgecombe: 17.3p 4.5r 4.0a
- Paul George: 13.3p 6.5r 3.5a

**MEM 주요선수:**
- Santi Aldama: 21.8p 7.8r 3.2a
- Jaren Jackson Jr.: 21.8p 7.0r 1.6a
- Cam Spencer: 14.2p 4.0r 8.8a

**추천**: Memphis Grizzlies 승 | **신뢰도**: ⭐⭐⭐⭐

---

## 🎯 경기 2: Boston Celtics @ Utah Jazz

**BOS**: 4승 1패 (80.0%) | 
**UTAH**: 2승 3패 (40.0%)

**BOS 주요선수:**
- Jaylen Brown: 32.0p 7.0r 4.3a
- Derrick White: 20.0p 5.0r 5.6a
- Payton Pritchard: 18.2p 5.6r 5.8a

**UTAH 주요선수:**
- Keyonte George: 26.0p 5.2r 6.8a
- Jusuf Nurkic: 13.3p 10.0r 5.5a
- Brice Sensabaugh: 12.2p 3.4r 2.2a

**추천**: Boston Celtics 승 | **신뢰도**: ⭐⭐⭐⭐⭐

---

## 🎯 경기 3: Detroit Pistons @ Los Angeles Lakers

**DET**: 3승 2패 (60.0%) | 
**LAL**: 1승 4패 (20.0%)

**DET 주요선수:**
- Cade Cunningham: 23.0p 6.6r 11.8a
- Jalen Duren: 19.1p 11.0r 2.0a
- Tobias Harris: 14.8p 4.0r 3.2a

**LAL 주요선수:**
- LeBron James: 27.7p 3.0r 4.7a
- Luka Doncic: 23.0p 5.0r 4.5a
- Nick Smith Jr.: 14.0p 2.3r 1.0a

**추천**: Detroit Pistons 승 | **신뢰도**: ⭐⭐⭐⭐⭐

---

## 🎯 경기 4: Sacramento Kings @ Los Angeles Clippers

**SAC**: 2승 3패 (40.0%) | 
**LAC**: 4승 1패 (80.0%)

**SAC 주요선수:**
- DeMar DeRozan: 22.0p 4.0r 5.8a
- Russell Westbrook: 17.8p 7.4r 5.6a
- Dennis Schroder: 15.2p 3.6r 6.2a

**LAC 주요선수:**
- Kawhi Leonard: 39.0p 9.7r 4.0a
- James Harden: 28.0p 3.5r 7.2a
- Brook Lopez: 13.5p 5.8r 1.8a

**추천**: Los Angeles Clippers 승 | **신뢰도**: ⭐⭐⭐⭐⭐

---

## 🎲 종합 추천

- **Memphis Grizzlies** (⭐⭐⭐⭐)
- **Boston Celtics** (⭐⭐⭐⭐⭐)
- **Detroit Pistons** (⭐⭐⭐⭐⭐)
- **Los Angeles Clippers** (⭐⭐⭐⭐⭐)

---

**Generated**: 2025-12-31 10:00:46 KST