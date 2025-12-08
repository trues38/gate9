import os
import json
import csv
import glob
import re
import sys
from tqdm import tqdm

# Increase CSV field size limit just in case
csv.field_size_limit(sys.maxsize)

def load_ticker_map(map_path):
    """
    Loads master_ticker_map.json and builds a lookup dictionary.
    Returns:
        lookup: dict {keyword_lower: ticker}
        keywords: list of keywords sorted by length (descending)
    """
    print(f"Loading ticker map from {map_path}...")
    with open(map_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    lookup = {}
    
    # Blacklist of common words that should NEVER be used as ticker keywords
    BLACKLIST = {
        "TOP", "WORLD", "POLITICS", "PRO", "NEW", "BEST", "GAP", "OUT",
        "LOW", "BIG", "ALL", "ONE", "SEE", "RUN", "FLY", "EAT", "KEY",
        "ART", "FUN", "WIN", "JOB", "CAR", "BUS", "AIR", "SKY", "SEA",
        "SUN", "MOON", "STAR", "GOLD", "SILVER", "OIL", "GAS", "CORN",
        "RICE", "COFFEE", "SUGAR", "COTTON", "COCOA", "WHEAT", "SOYBEAN",
        "WATER", "POWER", "ENERGY", "COAL", "URANIUM", "STEEL", "IRON",
        "SALT", "SAND", "GLASS", "WOOD", "PAPER", "PLASTIC", "TIME", "DATE",
        "DAY", "WEEK", "MONTH", "YEAR", "NOW", "THEN", "HERE", "THERE",
        "WHO", "WHAT", "WHERE", "WHEN", "WHY", "HOW", "WHICH", "THAT",
        "THIS", "THESE", "THOSE", "IT", "HE", "SHE", "THEY", "WE", "YOU",
        "GOOD", "BAD", "BETTER", "WORSE", "BEST", "WORST", "HIGH", "LOW",
        "UP", "DOWN", "LEFT", "RIGHT", "FRONT", "BACK", "SIDE", "CENTER",
        "MIDDLE", "TOP", "BOTTOM", "START", "END", "BEGIN", "FINISH",
        "OPEN", "CLOSE", "BUY", "SELL", "HOLD", "KEEP", "DROP", "RISE",
        "FALL", "JUMP", "DIVE", "WALK", "RUN", "SWIM", "FLY", "DRIVE",
        "RIDE", "SAIL", "ROW", "PADDLE", "CLIMB", "CRAWL", "SLIDE", "SLIP",
        "GLIDE", "DRIFT", "FLOAT", "SINK", "DROWN", "BURN", "FREEZE",
        "MELT", "BOIL", "COOK", "EAT", "DRINK", "SLEEP", "WAKE", "REST",
        "WORK", "PLAY", "GAME", "SPORT", "MATCH", "RACE", "FIGHT", "WAR",
        "PEACE", "LOVE", "HATE", "LIKE", "DISLIKE", "JOY", "SADNESS",
        "ANGER", "FEAR", "HOPE", "DREAM", "WISH", "WANT", "NEED", "HAVE",
        "HAS", "HAD", "DO", "DOES", "DID", "CAN", "COULD", "WILL", "WOULD",
        "SHALL", "SHOULD", "MAY", "MIGHT", "MUST", "OUGHT", "BE", "AM",
        "IS", "ARE", "WAS", "WERE", "BEEN", "BEING", "GET", "GOT", "GOTTEN",
        "TAKE", "TOOK", "TAKEN", "GIVE", "GAVE", "GIVEN", "MAKE", "MADE",
        "KNOW", "KNEW", "KNOWN", "THINK", "THOUGHT", "SEE", "SAW", "SEEN",
        "LOOK", "WATCH", "LISTEN", "HEAR", "HEARD", "FEEL", "FELT", "TOUCH",
        "SMELL", "TASTE", "SAY", "SAID", "TELL", "TOLD", "ASK", "ANSWER",
        "REPLY", "RESPOND", "SPEAK", "SPOKE", "SPOKEN", "TALK", "WRITE",
        "WROTE", "WRITTEN", "READ", "SHOW", "SHOWN", "HIDE", "HIDDEN",
        "FIND", "FOUND", "LOSE", "LOST", "WIN", "WON", "BEAT", "BEATEN",
        "DRAW", "DREW", "DRAWN", "CUT", "SLICE", "CHOP", "BREAK", "BROKE",
        "BROKEN", "TEAR", "TORE", "TORN", "SPLIT", "CRACK", "CRUSH", "SMASH",
        "HIT", "STRIKE", "STRUCK", "KICK", "PUNCH", "SLAP", "BANG", "BUMP",
        "CRASH", "COLLIDE", "WRECK", "RUIN", "DESTROY", "DAMAGE", "HARM",
        "HURT", "INJURE", "WOUND", "KILL", "MURDER", "DIE", "DEAD", "DEATH",
        "LIFE", "LIVE", "BORN", "BIRTH", "GROW", "GREW", "GROWN", "AGE",
        "OLD", "YOUNG", "NEW", "MODERN", "ANCIENT", "PAST", "PRESENT",
        "FUTURE", "HISTORY", "STORY", "TALE", "NEWS", "REPORT", "PAPER",
        "BOOK", "TEXT", "WORD", "LETTER", "NOTE", "MEMO", "FILE", "DATA",
        "INFO", "FACT", "TRUTH", "LIE", "MYTH", "IDEA", "PLAN", "GOAL",
        "AIM", "TARGET", "MARK", "POINT", "SPOT", "DOT", "LINE", "SHAPE",
        "FORM", "SIZE", "COLOR", "SOUND", "NOISE", "MUSIC", "SONG", "ART",
        "PICTURE", "IMAGE", "PHOTO", "VIDEO", "MOVIE", "FILM", "SHOW",
        "ACT", "SCENE", "STAGE", "SCREEN", "VIEW", "SIGHT", "VISION",
        "EYE", "EAR", "NOSE", "MOUTH", "FACE", "HEAD", "HAIR", "BODY",
        "ARM", "LEG", "HAND", "FOOT", "SKIN", "BONE", "BLOOD", "HEART",
        "MIND", "SOUL", "SPIRIT", "GHOST", "GOD", "DEVIL", "ANGEL", "DEMON",
        "HEAVEN", "HELL", "WORLD", "EARTH", "LAND", "SEA", "SKY", "SPACE",
        "STAR", "PLANET", "MOON", "SUN", "UNIVERSE", "NATURE", "ANIMAL",
        "PLANT", "TREE", "FLOWER", "BIRD", "FISH", "DOG", "CAT", "HORSE",
        "COW", "PIG", "SHEEP", "GOAT", "CHICKEN", "DUCK", "GOOSE", "MOUSE",
        "RAT", "RABBIT", "LION", "TIGER", "BEAR", "WOLF", "FOX", "DEER",
        "MONKEY", "APE", "MAN", "WOMAN", "BOY", "GIRL", "CHILD", "KID",
        "BABY", "ADULT", "PARENT", "FATHER", "MOTHER", "SON", "DAUGHTER",
        "BROTHER", "SISTER", "FRIEND", "ENEMY", "FAMILY", "GROUP", "TEAM",
        "CROWD", "PEOPLE", "PERSON", "HUMAN", "SOCIETY", "CULTURE", "NATION",
        "COUNTRY", "STATE", "CITY", "TOWN", "VILLAGE", "HOME", "HOUSE",
        "BUILDING", "ROOM", "DOOR", "WINDOW", "WALL", "FLOOR", "ROOF",
        "STREET", "ROAD", "PATH", "WAY", "BRIDGE", "TUNNEL", "PARK",
        "GARDEN", "SCHOOL", "COLLEGE", "UNIVERSITY", "CLASS", "LESSON",
        "TEACHER", "STUDENT", "BOOK", "PEN", "PENCIL", "PAPER", "DESK",
        "CHAIR", "TABLE", "BED", "SOFA", "LAMP", "LIGHT", "FAN", "CLOCK",
        "WATCH", "PHONE", "COMPUTER", "RADIO", "TV", "CAMERA", "CAR",
        "BUS", "TRAIN", "PLANE", "SHIP", "BOAT", "BIKE", "TRUCK", "VAN",
        "TAXI", "CAB", "DRIVER", "PILOT", "CAPTAIN", "CREW", "PASSENGER",
        "TICKET", "FARE", "PRICE", "COST", "VALUE", "MONEY", "CASH",
        "COIN", "BILL", "CHECK", "CARD", "BANK", "STORE", "SHOP", "MARKET",
        "MALL", "SALE", "DEAL", "OFFER", "PRICE", "DISCOUNT", "CHEAP",
        "EXPENSIVE", "RICH", "POOR", "FREE", "PAID", "OWE", "DEBT", "LOAN",
        "TAX", "FEE", "FINE", "RENT", "LEASE", "BUY", "SELL", "TRADE",
        "EXCHANGE", "BUSINESS", "COMPANY", "FIRM", "CORP", "INC", "LTD",
        "LLC", "CEO", "CFO", "COO", "MANAGER", "BOSS", "WORKER", "STAFF",
        "JOB", "CAREER", "PROFESSION", "TRADE", "CRAFT", "SKILL", "TOOL",
        "MACHINE", "ENGINE", "MOTOR", "FUEL", "OIL", "GAS", "POWER",
        "ENERGY", "FORCE", "STRENGTH", "WEAKNESS", "HEALTH", "SICKNESS",
        "DISEASE", "CURE", "MEDICINE", "DRUG", "PILL", "DOCTOR", "NURSE",
        "PATIENT", "HOSPITAL", "CLINIC", "SURGERY", "OPERATION", "TEST",
        "EXAM", "STUDY", "RESEARCH", "SCIENCE", "MATH", "ART", "HISTORY",
        "LANGUAGE", "ENGLISH", "KOREAN", "CHINESE", "JAPANESE", "FRENCH",
        "GERMAN", "SPANISH", "ITALIAN", "RUSSIAN", "ARABIC", "HINDI",
        "LATIN", "GREEK", "HEBREW", "SANSKRIT", "CODE", "CIPHER", "KEY",
        "LOCK", "SAFE", "GUARD", "POLICE", "ARMY", "NAVY", "AIR", "FORCE",
        "WAR", "BATTLE", "FIGHT", "ATTACK", "DEFEND", "PROTECT", "SAVE",
        "RESCUE", "HELP", "AID", "ASSIST", "SUPPORT", "SERVE", "OBEY",
        "LEAD", "GUIDE", "DIRECT", "RULE", "GOVERN", "CONTROL", "MANAGE",
        "ORDER", "COMMAND", "DEMAND", "REQUEST", "ASK", "BEG", "PRAY",
        "VOTE", "ELECT", "CHOOSE", "DECIDE", "JUDGE", "COURT", "LAW",
        "LEGAL", "ILLEGAL", "CRIME", "SIN", "WRONG", "RIGHT", "JUST",
        "FAIR", "UNFAIR", "EQUAL", "FREE", "SLAVE", "MASTER", "SERVANT",
        "KING", "QUEEN", "PRINCE", "PRINCESS", "LORD", "LADY", "KNIGHT",
        "NOBLE", "ROYAL", "COMMON", "PUBLIC", "PRIVATE", "SECRET", "OPEN",
        "CLOSED", "LOCKED", "UNLOCKED", "SAFE", "DANGER", "RISK", "CHANCE",
        "LUCK", "FATE", "DESTINY", "FORTUNE", "DOOM", "RUIN", "FAIL",
        "SUCCEED", "WIN", "LOSE", "VICTORY", "DEFEAT", "GAIN", "LOSS",
        "PROFIT", "BENEFIT", "ADVANTAGE", "USE", "UTILITY", "VALUE", "WORTH",
        "QUALITY", "QUANTITY", "NUMBER", "COUNT", "TOTAL", "SUM", "PART",
        "WHOLE", "PIECE", "BIT", "CHUNK", "BLOCK", "SLICE", "CUT",
        "SECTION", "SEGMENT", "DIVISION", "UNIT", "ITEM", "OBJECT", "THING",
        "STUFF", "MATTER", "SUBSTANCE", "MATERIAL", "ELEMENT", "ATOM",
        "MOLECULE", "CELL", "ORGAN", "SYSTEM", "PROCESS", "METHOD", "WAY",
        "MODE", "STYLE", "FORM", "SHAPE", "PATTERN", "DESIGN", "PLAN",
        "MAP", "CHART", "GRAPH", "TABLE", "LIST", "INDEX", "CATALOG",
        "MENU", "GUIDE", "MANUAL", "BOOK", "TEXT", "SCRIPT", "CODE",
        "PROGRAM", "APP", "SOFT", "HARD", "WARE", "NET", "WEB",
        "SITE", "PAGE", "LINK", "CLICK", "TAP", "TYPE", "PRINT",
        "COPY", "PASTE", "CUT", "SAVE", "LOAD", "OPEN", "CLOSE",
        "FILE", "FOLDER", "DIR", "PATH", "DRIVE", "DISK", "CHIP",
        "CARD", "BOARD", "SCREEN", "DISPLAY", "VIEW", "SHOW", "HIDE",
        "SEARCH", "FIND", "QUERY", "ASK", "ANSWER", "RESULT", "OUTPUT",
        "INPUT", "DATA", "INFO", "USER", "ADMIN", "GUEST", "MEMBER",
        "CLIENT", "SERVER", "HOST", "NODE", "PEER", "LINK", "CONN",
        "PORT", "SOCKET", "PIPE", "STREAM", "FLOW", "CHANNEL", "BAND",
        "WAVE", "FREQ", "SIGNAL", "NOISE", "ERROR", "BUG", "FAULT",
        "FAIL", "CRASH", "HANG", "FREEZE", "LAG", "SLOW", "FAST",
        "SPEED", "RATE", "TIME", "DATE", "CLOCK", "TIMER", "ALARM",
        "WAKE", "SLEEP", "WAIT", "PAUSE", "STOP", "START", "RUN",
        "EXEC", "CALL", "RET", "JMP", "MOV", "ADD", "SUB",
        "MUL", "DIV", "MOD", "AND", "OR", "XOR", "NOT",
        "NEG", "INC", "DEC", "CMP", "TEST", "SET", "CLR",
        "FLAG", "BIT", "BYTE", "WORD", "DWORD", "QWORD", "FLOAT",
        "DOUBLE", "CHAR", "STR", "INT", "LONG", "SHORT", "BOOL",
        "TRUE", "FALSE", "NULL", "VOID", "PTR", "REF", "VAL",
        "VAR", "CONST", "STATIC", "EXTERN", "PUBLIC", "PRIVATE", "PROTECTED",
        "CLASS", "STRUCT", "UNION", "ENUM", "TYPEDEF", "TEMPLATE", "VIRTUAL",
        "OVERRIDE", "FINAL", "FRIEND", "INLINE", "ASM", "VOLATILE", "REGISTER",
        "AUTO", "THREAD", "TASK", "PROC", "FUNC", "METHOD", "LAMBDA",
        "BLOCK", "SCOPE", "STACK", "HEAP", "QUEUE", "DEQUE", "LIST",
        "VECTOR", "MAP", "SET", "TREE", "GRAPH", "NODE", "EDGE",
        "VERTEX", "ROOT", "LEAF", "CHILD", "PARENT", "SIB", "ANCESTOR",
        "DESCENDANT", "KIN", "CLAN", "TRIBE", "RACE", "SPECIES", "GENUS",
        "FAMILY", "ORDER", "CLASS", "PHYLUM", "KINGDOM", "DOMAIN", "LIFE"
    }
    
    for ticker, info in data.items():
        keywords = []
        if info.get("name_en"):
            keywords.append(info["name_en"])
        if info.get("name_kr"):
            keywords.append(info["name_kr"])
        if info.get("aliases"):
            keywords.extend(info["aliases"])
            
        # Also map the ticker symbol itself (e.g. "AAPL")
        symbol = ticker.split(":")[-1]
        if len(symbol) >= 3: 
             keywords.append(symbol)

        for kw in keywords:
            if not kw: continue
            kw_clean = kw.strip().lower()
            if not kw_clean: continue
            
            # Enforce minimum length of 4 to reduce false positives
            if len(kw_clean) < 4: continue
            
            # Check Blacklist
            if kw_clean.upper() in BLACKLIST:
                continue
            
            if kw_clean not in lookup:
                lookup[kw_clean] = ticker
            else:
                # Prefer US ticker if collision
                if ticker.startswith("US:") and not lookup[kw_clean].startswith("US:"):
                    lookup[kw_clean] = ticker
                    
    print(f"Built lookup map with {len(lookup)} keywords.")
    return lookup

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def build_regex_pattern(keywords):
    # Sort by length desc to ensure longest match first
    sorted_kws = sorted(keywords, key=len, reverse=True)
    # Escape special chars
    escaped = [re.escape(k) for k in sorted_kws]
    # Create pattern: (kw1|kw2|...)
    # Use word boundaries \b for English, but for Korean it might be tricky.
    # For mixed, maybe just simple substring or try to be smart.
    # Let's use simple substring for now to catch everything, or \b for English parts?
    # Use word boundaries to prevent partial matches (e.g. "Apple" in "Pineapple")
    pattern_str = "|".join(escaped)
    # Wrap in word boundaries
    final_pattern = r'\b(' + pattern_str + r')\b'
    return re.compile(final_pattern, re.IGNORECASE)

def process_files(input_dir, lookup_map):
    jsonl_files = glob.glob(os.path.join(input_dir, "*.jsonl"))
    print(f"Found {len(jsonl_files)} JSONL files in {input_dir}")
    
    events = []
    seen_titles = set()
    
    # Build Regex
    # If too large, we might need to chunk. 
    # Python re limit is quite high (approx 2GB pattern buffer), so 20k keywords should fit.
    print("Building regex pattern...")
    keywords = list(lookup_map.keys())
    try:
        regex = build_regex_pattern(keywords)
    except Exception as e:
        print(f"Regex build failed: {e}. Fallback to chunking or slower method?")
        # Fallback: simple iteration (slow) or chunking. 
        # Let's hope it works.
        return []

    print("Processing files...")
    for filepath in jsonl_files:
        filename = os.path.basename(filepath)
        print(f"Reading {filename}...")
        
        # Count lines for tqdm
        # num_lines = sum(1 for _ in open(filepath)) # Slow to count
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in tqdm(f, desc=filename, unit="lines"):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    title = data.get("title", "")
                    if not title: continue
                    
                    title_clean = clean_text(title)
                    if title_clean in seen_titles:
                        continue
                    seen_titles.add(title_clean)
                    
                    # Regex Match
                    match = regex.search(title_clean)
                    matched_ticker = None
                    if match:
                        # match.group() gives the matched text as it appears in string
                        # We need to look it up in lower case
                        matched_text = match.group().lower()
                        matched_ticker = lookup_map.get(matched_text)
                    
                    if matched_ticker:
                        data["ticker"] = matched_ticker
                        
                    row = {
                        "ticker": data.get("ticker", ""),
                        "title": title_clean,
                        "published_at": data.get("published_at", "") or data.get("date", ""),
                        "source": data.get("source", ""),
                        "url": data.get("url", "") or data.get("link", ""),
                        "summary": clean_text(data.get("summary", "") or data.get("content", "")[:200]),
                    }
                    events.append(row)
                    
                except json.JSONDecodeError:
                    continue
                    
    return events

def save_to_csv(events, output_path):
    if not events:
        print("No events to save.")
        return
        
    headers = ["ticker", "title", "published_at", "source", "url", "summary"]
    
    print(f"Saving {len(events)} events to {output_path}...")
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(events)
    print("Done.")

if __name__ == "__main__":
    BASE_DIR = "/Users/js/g9"
    MAP_PATH = os.path.join(BASE_DIR, "ticker_global/master_ticker_map.json")
    INPUT_DIR = os.path.join(BASE_DIR, "ticker_global/US/row")
    OUTPUT_CSV = os.path.join(BASE_DIR, "ticker_global/US/cleaned_events_final.csv")
    
    if not os.path.exists(MAP_PATH):
        print(f"Error: Map file not found at {MAP_PATH}")
        exit(1)
        
    lookup = load_ticker_map(MAP_PATH)
    events = process_files(INPUT_DIR, lookup)
    save_to_csv(events, OUTPUT_CSV)
