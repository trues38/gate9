# regime_definitions.py

REGIMES = {
    "R01": {
        "name": "광야 (The Wilderness)",
        "keywords": ["광야", "빈들", "사막", "마른", "목마른", "길이 없는", "낮아지게", "주리게", "시험", "40일", "40년"],
        "keywords_en": ["wilderness", "desert", "dry", "thirsty", "waste", "solitary", "hunger", "tempt", "test", "forty days", "forty years"],
        "desc": "하나님만 의지해야 하는 고립과 연단의 시간",
        "archetypes": ["모세", "세례요한"]
    },
    "R02": {
        "name": "구덩이 (The Pit)",
        "keywords": ["감옥", "지하", "깊은 곳", "웅덩이", "갇힌", "사슬", "어두운", "흑암", "죽음의", "스올"],
        "keywords_en": ["pit", "prison", "dungeon", "deep", "darkness", "chain", "bound", "sheol", "grave", "trapped", "miry clay"],
        "desc": "내 힘으로 빠져나올 수 없는 절대적 절망과 단절",
        "archetypes": ["요셉", "예레미야"]
    },
    "R03": {
        "name": "배신 (The Betrayal)",
        "keywords": ["배반", "친구", "입맞춤", "칼", "도망", "원수", "모략", "속임수", "등을 돌리다"],
        "keywords_en": ["betray", "traitor", "friend", "kiss", "sword", "enemy", "plot", "deceit", "forsake", "conspire"],
        "desc": "믿었던 관계의 깨어짐과 깊은 상처",
        "archetypes": ["다윗", "예수님"]
    },
    "R04": {
        "name": "회복 (The Restoration)",
        "keywords": ["다시", "세우다", "고치다", "돌아오다", "회복", "성벽", "기초", "옛적", "치유", "싸매다"],
        "keywords_en": ["restore", "rebuild", "heal", "return", "repair", "wall", "foundation", "breach", "cure", "bind up", "renew"],
        "desc": "무너진 것을 다시 세우고 본래의 자리로 돌아감",
        "archetypes": ["느헤미야", "베드로"]
    },
    "R05": {
        "name": "소명 (The Calling)",
        "keywords": ["부르시다", "가라", "보내다", "선지자", "종", "명령", "떨기나무", "사명", "택한"],
        "keywords_en": ["call", "go", "send", "sent", "servant", "prophet", "command", "bush", "choose", "elect", "appoint"],
        "desc": "거부할 수 없는 하나님의 목적과 임무",
        "archetypes": ["아브라함", "바울"]
    },
    "R06": {
        "name": "희생 (The Sacrifice)",
        "keywords": ["제물", "피", "드리다", "바치다", "독자", "어린양", "십자가", "죽임", "대속"],
        "keywords_en": ["sacrifice", "offering", "blood", "lamb", "cross", "slain", "atonement", "altar", "price", "ransom"],
        "desc": "더 큰 가치를 위해 소중한 것을 내어놓음",
        "archetypes": ["아브라함(이삭)", "예수님"]
    },
    "R07": {
        "name": "혼돈 (The Chaos)",
        "keywords": ["홍수", "바벨", "흩어짐", "섞임", "혼잡", "깊음", "물", "심판", "멸망"],
        "keywords_en": ["flood", "scatter", "confuse", "deep", "waters", "void", "formless", "darkness", "destroy", "perish"],
        "desc": "질서가 무너지고 통제 불가능한 상태",
        "archetypes": ["노아", "바벨탑"]
    },
    "R08": {
        "name": "질서 (The Order)",
        "keywords": ["율법", "규례", "법도", "계명", "성막", "치수", "식양", "지혜", "분별"],
        "keywords_en": ["law", "commandment", "statute", "ordinance", "sanctuary", "pattern", "wisdom", "measure", "decree", "order"],
        "desc": "하나님의 성품이 반영된 구조와 경계",
        "archetypes": ["레위기", "솔로몬"]
    },
    "R09": {
        "name": "유배 (The Exile)",
        "keywords": ["포로", "이방", "강가", "그울", "예루살렘을 향하여", "다니엘", "잡혀감", "낯선"],
        "keywords_en": ["exile", "captive", "captivity", "stranger", "river", "babylon", "foreign", "weep", "remember zion"],
        "desc": "약속의 땅을 떠나 이방에서 겪는 정체성의 싸움",
        "archetypes": ["다니엘", "에스겔"]
    },
    "R10": {
        "name": "출애굽 (The Exodus)",
        "keywords": ["탈출", "건너다", "해방", "자유", "홍해", "유월절", "나오다", "인도하여"],
        "keywords_en": ["exodus", "deliver", "bondage", "egypt", "sea", "pass over", "passover", "lead out", "free", "loose"],
        "desc": "억압에서 벗어나 새로운 정체성으로 이동",
        "archetypes": ["이스라엘"]
    },
    "R11": {
        "name": "기다림 (The Waiting)",
        "keywords": ["잠잠히", "바라다", "기다리다", "인내", "언제까지", "파수꾼", "더딘", "약속"],
        "keywords_en": ["wait", "patience", "tarry", "how long", "watchman", "hope", "trust", "silent", "expect"],
        "desc": "하나님의 때를 신뢰하며 견디는 시간",
        "archetypes": ["시므온", "다윗"]
    },
    "R12": {
        "name": "전쟁 (The Battle)",
        "keywords": ["싸움", "대적", "군대", "무기", "승리", "용사", "여호와의 이름", "전신갑주"],
        "keywords_en": ["battle", "war", "fight", "enemy", "adversary", "sword", "shield", "victory", "army", "host", "triumph"],
        "desc": "영적/물리적 대적과의 충돌과 돌파",
        "archetypes": ["여호수아", "다윗"]
    },
    "R13": {
        "name": "잔치 (The Feast)",
        "keywords": ["혼인", "포도주", "기쁨", "즐거움", "노래", "춤", "풍성", "초대", "잔치"],
        "keywords_en": ["feast", "wedding", "marriage", "wine", "joy", "gladness", "rejoice", "dance", "banquet", "supper"],
        "desc": "하나님 안에서 누리는 풍요와 기쁨의 절정",
        "archetypes": ["가나혼인잔치", "어린양혼인잔치"]
    },
    "R14": {
        "name": "기근 (The Famine)",
        "keywords": ["흉년", "기근", "굶주림", "가뭄", "비가 오지 아니하며", "양식", "말라", "시내"],
        "keywords_en": ["famine", "hunger", "starve", "drought", "dry", "wither", "no rain", "lack", "bread"],
        "desc": "생존을 위협하는 결핍과 마름",
        "archetypes": ["엘리야", "탕자"]
    },
    "R15": {
        "name": "언약 (The Covenant)",
        "keywords": ["맹세", "언약", "약속", "영원한", "지키다", "기억하다", "자손", "복"],
        "keywords_en": ["covenant", "oath", "promise", "swear", "forever", "everlasting", "keep", "remnant", "seed", "bless"],
        "desc": "변치 않는 신실한 관계의 맺음",
        "archetypes": ["아브라함", "다윗"]
    },
    "R16": {
        "name": "심판 (The Judgment)",
        "keywords": ["진노", "화", "공의", "보응", "불", "재앙", "경고", "망하리라"],
        "keywords_en": ["judgment", "judge", "wrath", "fire", "anger", "woe", "consume", "punish", "desolate", "recompense"],
        "desc": "죄에 대한 하나님의 엄중한 대응과 바로잡음",
        "archetypes": ["선지서", "계시록"]
    },
    "R17": {
        "name": "은혜 (The Grace)",
        "keywords": ["긍휼", "자비", "용서", "값없이", "선물", "불쌍히", "탕감", "사랑"],
        "keywords_en": ["grace", "mercy", "compassion", "forgive", "pardon", "gift", "love", "kindness", "favor"],
        "desc": "자격 없는 자에게 주어지는 압도적 호의",
        "archetypes": ["므비보셋", "삭개오"]
    },
    "R18": {
        "name": "지혜 (The Wisdom)",
        "keywords": ["지혜", "명철", "지식", "훈계", "슬기", "깨달음", "미련한 자", "잠언"],
        "keywords_en": ["wisdom", "wise", "understanding", "knowledge", "instruction", "prudent", "proverb", "discern"],
        "desc": "세상을 움직이는 하나님의 원리를 꿰뚫어 봄",
        "archetypes": ["솔로몬"]
    },
    "R19": {
        "name": "어리석음 (The Folly)",
        "keywords": ["미련", "어리석은", "교만", "넘어짐", "멸망의 선봉", "고집", "듣지 아니하고"],
        "keywords_en": ["folly", "fool", "foolish", "pride", "haughty", "stubborn", "rebel", "stiff-necked", "fall"],
        "desc": "자아도취로 인해 스스로 파멸로 걸어감",
        "archetypes": ["사울", "르호보암"]
    },
    "R20": {
        "name": "정체성 (The Identity)",
        "keywords": ["이름", "아들", "자녀", "백성", "택한", "거룩한", "왕 같은", "제사장"],
        "keywords_en": ["name", "son", "daughter", "child", "people", "holy", "chosen", "royal", "priest", "heritage"],
        "desc": "내가 누구인지에 대한 근원적 정의",
        "archetypes": ["야곱(이스라엘)"]
    },
    "R21": {
        "name": "가족 (The Family)",
        "keywords": ["형제", "부모", "자녀", "아내", "남편", "집", "유업", "화목"],
        "keywords_en": ["brother", "sister", "father", "mother", "wife", "husband", "family", "house", "household"],
        "desc": "혈연 공동체 안에서의 갈등과 사랑",
        "archetypes": ["요셉의 형제들", "마리아와 마르다"]
    },
    "R22": {
        "name": "왕권 (The Kingship)",
        "keywords": ["왕", "다스리다", "통치", "보좌", "권세", "영광", "나라", "주"],
        "keywords_en": ["king", "reign", "throne", "dominion", "power", "glory", "kingdom", "rule", "majesty"],
        "desc": "책임지는 리더십과 권위의 올바른 행사",
        "archetypes": ["다윗", "예수님"]
    },
    "R23": {
        "name": "종됨 (Ebed/Servanthood)",
        "keywords": ["종", "섬기다", "낮은", "발을 씻기다", "순종", "받들다", "충성"],
        "keywords_en": ["servant", "serve", "bondservant", "service", "wash", "feet", "humble", "obey", "faithful"],
        "desc": "가장 낮은 곳에서 섬김으로 위대해짐",
        "archetypes": ["고난받는 종"]
    },
    "R24": {
        "name": "부활 (The Resurrection)",
        "keywords": ["살아나다", "생명", "일어나다", "무덤", "사망을 이기고", "첫 열매", "영생"],
        "keywords_en": ["resurrection", "rise", "risen", "live", "life", "grave", "death", "alive", "firstfruits"],
        "desc": "죽음을 이기고 새로운 차원의 생명으로 나아감",
        "archetypes": ["나사로", "예수님"]
    },
    "R25": {
        "name": "애가 (The Lament)",
        "keywords": ["눈물", "슬픔", "곡", "탄식", "부르짖다", "상한 심령", "괴로움"],
        "keywords_en": ["lament", "weep", "tears", "cry", "mourn", "sorrow", "sigh", "groan", "grief", "broken"],
        "desc": "고통을 하나님 앞에 정직하게 쏟아냄",
        "archetypes": ["시편", "예레미야애가"]
    },
    "R26": {
        "name": "찬양 (The Praise)",
        "keywords": ["찬양", "송축", "노래", "감사", "높이다", "경배", "영광", "할렐루야"],
        "keywords_en": ["praise", "sing", "song", "bless", "exalt", "worship", "thanksgiving", "magnify", "hallelujah"],
        "desc": "상황을 넘어 하나님의 어떠하심을 선포함",
        "archetypes": ["미리암", "다윗"]
    },
    "R27": {
        "name": "시험 (The Temptation)",
        "keywords": ["시험", "유혹", "선악과", "뱀", "먹음직", "보암직", "욕심", "죄"],
        "keywords_en": ["tempt", "temptation", "test", "serpent", "desire", "lust", "sin", "transgress", "eat", "fruit"],
        "desc": "욕망과 계명 사이에서의 치열한 갈등",
        "archetypes": ["하와", "광야 시험"]
    },
    "R28": {
        "name": "비전 (The Vision)",
        "keywords": ["환상", "꿈", "이상", "보라", "계시", "장래 일", "하늘이 열리고"],
        "keywords_en": ["vision", "dream", "revelation", "behold", "see", "eyes", "heaven open", "prophecy"],
        "desc": "보이지 않는 미래와 천상의 현실을 봄",
        "archetypes": ["다니엘", "요한"]
    },
    "R29": {
        "name": "침묵 (The Silence)",
        "keywords": ["대답지 아니하시다", "숨으시다", "찾지 못하고", "어디 계시니이까", "밤"],
        "keywords_en": ["silence", "silent", "answer not", "hide", "darkness", "night", "seek", "where", "absent"],
        "desc": "하나님의 부재 속에서 믿음을 지키는 싸움",
        "archetypes": ["욥"]
    },
    "R30": {
        "name": "성육신 (The Incarnation)",
        "keywords": ["육신", "거하다", "우리와 함께", "임마누엘", "장막", "사람의 모양"],
        "keywords_en": ["flesh", "dwell", "tabernacle", "manifest", "among us", "likeness", "form", "son of man"],
        "desc": "신이 인간의 삶의 자리로 들어오심",
        "archetypes": ["성막", "예수님"]
    }
}
