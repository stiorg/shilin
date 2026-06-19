import random
import os
import json

BOPOMOFO_DICT = {
    "ㄅ": "b", "ㄆ": "p", "ㄇ": "m", "ㄈ": "f",
    "ㄉ": "d", "ㄊ": "t", "ㄋ": "n", "ㄌ": "l",
    "ㄍ": "g", "ㄎ": "k", "ㄏ": "h",
    "ㄐ": "ji", "ㄑ": "qi", "ㄒ": "xi",
    "ㄓ": "zhi", "ㄔ": "chi", "ㄕ": "shi", "ㄖ": "ri",
    "ㄗ": "zi", "ㄘ": "ci", "ㄙ": "si",
    "ㄚ": "a", "ㄛ": "o", "ㄜ": "e", "ㄝ": "e",
    "ㄞ": "ai", "ㄟ": "ei", "ㄠ": "ao", "ㄡ": "ou",
    "ㄢ": "an", "ㄣ": "en", "ㄤ": "ang", "ㄥ": "eng", "ㄦ": "er",
    "ㄧ": "yi", "ㄨ": "wu", "ㄩ": "yu"
}

DATA_FILE = "bopomofo_srs_data.json"

def load_game_data():
    """Loads progress and high scores. Initializes them if the file doesn't exist."""
    default_data = {
        "all_time_high_streak": 0,
        "intervals": {char: 1 for char in BOPOMOFO_DICT}
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "all_time_high_streak" in data and "intervals" in data:
                    return data
        except Exception:
            pass
    return default_data

def save_game_data(data):
    """Saves intervals and records to disk."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def play_endless(game_data):
    print("\n--- 🏃 ENDLESS SRS STREAK MODE ---")
    print("Type 'exit' to return to the main menu.\n")
    
    intervals = game_data["intervals"]
    current_streak = 0
    max_streak_this_session = 0

    while True:
        chars = list(BOPOMOFO_DICT.keys())
        weights = [1.0 / intervals[c] for c in chars]
        
        char = random.choices(chars, weights=weights, k=1)[0]
        correct_answer = BOPOMOFO_DICT[char]
        current_level = intervals[char]

        level_display = f"Lv.{current_level}" if current_level > 1 else "New"
        streak_display = f" | 🔥 Streak: {current_streak}" if current_streak > 0 else ""
        
        user_input = input(f"[{char}] ({level_display}){streak_display} -> Pinyin: ").strip().lower()

        if user_input == 'exit':
            break

        if user_input == correct_answer:
            current_streak += 1
            intervals[char] = min(current_level * 2, 32)
            print(f"✨ Correct! Level up -> {char} is now Lv.{intervals[char]}.")
            
            if current_streak > max_streak_this_session:
                max_streak_this_session = current_streak
            if max_streak_this_session > game_data["all_time_high_streak"]:
                game_data["all_time_high_streak"] = max_streak_this_session
                print("👑 NEW ALL-TIME HIGH STREAK!")
            print()
        else:
            if current_streak > 0:
                print(f"💥 Streak Broken! (You reached {current_streak})")
            print(f"❌ Incorrect. The correct answer was '{correct_answer}'.")
            print(f"📉 Resetting [{char}] back to basic rotation.\n")
            intervals[char] = 1
            current_streak = 0
            
    print(f"\nSession Max Streak: {max_streak_this_session}")
    save_game_data(game_data)

def play_focused_packs(game_data):
    print("\n--- 📦 FOCUSED SRS 5-PACK MODE ---")
    print("Clearing characters increases their SRS level. Mistakes reset them.")
    print("Type 'exit' to return to the main menu.\n")

    intervals = game_data["intervals"]
    chars = list(BOPOMOFO_DICT.keys())
    
    # Sort characters so that lower SRS levels (items you struggle with) are prioritized for the next packs!
    sorted_pool = sorted(chars, key=lambda c: intervals[c])
    
    pack_count = 1

    while sorted_pool:
        current_pack = sorted_pool[:5]
        sorted_pool = sorted_pool[5:]
        
        print(f"📦 Loading Pack #{pack_count} (Priority: characters you need to practice most)")
        print(f"Target characters: {', '.join(current_pack)}\n")
        
        while current_pack:
            random.shuffle(current_pack)
            remaining_this_round = []
            
            for char in current_pack:
                correct_answer = BOPOMOFO_DICT[char]
                current_level = intervals[char]
                
                level_display = f"Lv.{current_level}" if current_level > 1 else "New"
                user_input = input(f"[{char}] ({level_display}) -> Pinyin: ").strip().lower()
                
                if user_input == 'exit':
                    print("\nExiting pack mode... saving progress.")
                    save_game_data(game_data)
                    return

                if user_input == correct_answer:
                    intervals[char] = min(current_level * 2, 32)
                    print(f"✨ Correct! Level up -> Lv.{intervals[char]}.")
                else:
                    intervals[char] = 1
                    print(f"❌ Incorrect. The correct answer was '{correct_answer}'.")
                    print(f"📉 [{char}] reset to Lv.1. It stays in the pack.")
                    remaining_this_round.append(char)
            
            current_pack = remaining_this_round
            if current_pack:
                print(f"\n🔄 Reviewing the {len(current_pack)} character(s) missed in this pack...\n")
            else:
                print(f"\n🎉 Pack #{pack_count} CLEARED!\n")
                pack_count += 1
                save_game_data(game_data) # Auto-save after completing a pack
                
    print("🏆 AMAZING! You have reviewed all characters across all packs!")

def main():
    while True:
        game_data = load_game_data()
        all_time_high = game_data["all_time_high_streak"]

        print("=" * 45)
        print("         BOPOMOFO TRAINING CENTER        ")
        print("=" * 45)
        print(f"🏆 All-Time Max Streak Record: {all_time_high}")
        print("1. 🏃 Endless SRS Streak Mode")
        print("2. 📦 Focused SRS 5-Pack Mode")
        print("3. ❌ Exit Program")
        print("-" * 45)
        
        choice = input("Select a mode (1-3): ").strip()
        
        if choice == '1':
            play_endless(game_data)
        elif choice == '2':
            play_focused_packs(game_data)
        elif choice == '3':
            print("\nGoodbye! Keep practicing! 加油！")
            break
        else:
            print("\n⚠️ Invalid selection. Please type 1, 2, or 3.\n")

if __name__ == "__main__":
    main()