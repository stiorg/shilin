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
    default_data = {
        "all_time_high_streak": 0,
        "intervals": {char: 1 for char in BOPOMOFO_DICT},
        "confusion_matrix": {char: [] for char in BOPOMOFO_DICT}
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "all_time_high_streak" in data and "intervals" in data:
                    if "confusion_matrix" not in data:
                        data["confusion_matrix"] = {char: [] for char in BOPOMOFO_DICT}
                    return data
        except Exception:
            pass
    return default_data

def save_game_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def generate_dynamic_choices(correct_answer, char, game_data):
    """Generates 5 options prioritizing user's historic mistakes."""
    choices = [correct_answer]
    
    personal_mistakes = game_data["confusion_matrix"].get(char, []).copy()
    personal_mistakes = list(dict.fromkeys(reversed(personal_mistakes)))
    
    for mistake in personal_mistakes:
        if mistake != correct_answer and mistake not in choices:
            choices.append(mistake)
        if len(choices) == 5:
            break
            
    all_pinyins = list(set(BOPOMOFO_DICT.values()))
    while len(choices) < 5:
        rand_pinyin = random.choice(all_pinyins)
        if rand_pinyin not in choices:
            choices.append(rand_pinyin)
            
    random.shuffle(choices)
    return choices

def play_endless(game_data):
    print("\n--- 🏃 NUMERIC SRS ENDLESS MODE ---")
    print("Press [0] at any time to return to the main menu.\n")
    
    intervals = game_data["intervals"]
    confusion_matrix = game_data["confusion_matrix"]
    current_streak = 0
    max_streak_this_session = 0

    while True:
        chars = list(BOPOMOFO_DICT.keys())
        weights = [1.0 / intervals[c] for c in chars]
        char = random.choices(chars, weights=weights, k=1)[0]
        
        correct_answer = BOPOMOFO_DICT[char]
        choices = generate_dynamic_choices(correct_answer, char, game_data)
        
        # Map options to strings "1" through "5"
        mapping = {str(i+1): choices[i] for i in range(5)}

        level_display = f"Lv.{intervals[char]}" if intervals[char] > 1 else "New"
        streak_display = f" | 🔥 Streak: {current_streak}" if current_streak > 0 else ""
        
        print(f"👉 Character:  {char}  ({level_display}){streak_display}")
        for num in ["1", "2", "3", "4", "5"]:
            print(f"  [{num}] {mapping[num]}")
            
        user_input = input("Your answer (1-5 or 0 to exit): ").strip()

        if user_input == '0':
            break

        if user_input not in ["1", "2", "3", "4", "5"]:
            print("⚠️ Invalid choice! Press 1-5 to answer, or 0 to exit.\n")
            continue

        selected_pinyin = mapping[user_input]

        if selected_pinyin == correct_answer:
            current_streak += 1
            intervals[char] = min(intervals[char] * 2, 32)
            print(f"✨ Correct! {char} leveled up to Lv.{intervals[char]}.\n")
            
            if current_streak > max_streak_this_session:
                max_streak_this_session = current_streak
            if max_streak_this_session > game_data["all_time_high_streak"]:
                game_data["all_time_high_streak"] = max_streak_this_session
                print("👑 NEW ALL-TIME HIGH STREAK!")
        else:
            if current_streak > 0:
                print(f"💥 Streak Broken! (You hit {current_streak})")
            print(f"❌ Incorrect. Option [{user_input}] was '{selected_pinyin}'. The correct answer was '{correct_answer}'.")
            print(f"📉 Resetting [{char}] back to basic rotation.")
            
            if selected_pinyin not in confusion_matrix[char]:
                confusion_matrix[char].append(selected_pinyin)
            print(f"🧠 Logged mistake: System linked {char} with '{selected_pinyin}'.\n")
            
            intervals[char] = 1
            current_streak = 0
            
    print(f"\nSession Max Streak: {max_streak_this_session}")
    save_game_data(game_data)

def play_focused_packs(game_data):
    print("\n--- 📦 NUMERIC SRS 5-PACK MODE ---")
    print("Press [0] at any time to save and return to the menu.\n")

    intervals = game_data["intervals"]
    confusion_matrix = game_data["confusion_matrix"]
    chars = list(BOPOMOFO_DICT.keys())
    sorted_pool = sorted(chars, key=lambda c: intervals[c])
    pack_count = 1

    while sorted_pool:
        current_pack = sorted_pool[:5]
        sorted_pool = sorted_pool[5:]
        print(f"📦 Loading Pack #{pack_count}")
        print(f"Target characters: {', '.join(current_pack)}\n")
        
        while current_pack:
            random.shuffle(current_pack)
            remaining_this_round = []
            
            for char in current_pack:
                correct_answer = BOPOMOFO_DICT[char]
                choices = generate_dynamic_choices(correct_answer, char, game_data)
                mapping = {str(i+1): choices[i] for i in range(5)}

                level_display = f"Lv.{intervals[char]}" if intervals[char] > 1 else "New"
                print(f"👉 Character:  {char}  ({level_display})")
                for num in ["1", "2", "3", "4", "5"]:
                    print(f"  [{num}] {mapping[num]}")
                    
                user_input = input("Your answer (1-5 or 0 to exit): ").strip()
                
                if user_input == '0':
                    print("\nExiting pack mode... saving progress.")
                    save_game_data(game_data)
                    return

                if user_input not in ["1", "2", "3", "4", "5"]:
                    print("⚠️ Invalid choice! Penalized: Character remains in pack.\n")
                    remaining_this_round.append(char)
                    continue

                selected_pinyin = mapping[user_input]

                if selected_pinyin == correct_answer:
                    intervals[char] = min(intervals[char] * 2, 32)
                    print(f"✨ Correct! Leveled up to Lv.{intervals[char]}.\n")
                else:
                    intervals[char] = 1
                    if selected_pinyin not in confusion_matrix[char]:
                        confusion_matrix[char].append(selected_pinyin)
                        
                    print(f"❌ Incorrect. The correct answer was '{correct_answer}'.")
                    print(f"🧠 Logged mistake: System linked {char} with '{selected_pinyin}'.")
                    print(f"📉 [{char}] reset to Lv.1. It stays in the pack.\n")
                    remaining_this_round.append(char)
            
            current_pack = remaining_this_round
            if current_pack:
                print(f"🔄 Reviewing the {len(current_pack)} character(s) missed in this pack...\n")
            else:
                print(f"🎉 Pack #{pack_count} CLEARED!\n")
                pack_count += 1
                save_game_data(game_data)
                
    print("🏆 AMAZING! You have reviewed all characters across all packs!")

def main():
    while True:
        game_data = load_game_data()
        all_time_high = game_data["all_time_high_streak"]

        print("=" * 45)
        print("         BOPOMOFO TRAINING CENTER        ")
        print("=" * 45)
        print(f"🏆 All-Time Max Streak Record: {all_time_high}")
        print("1. 🏃 Endless SRS Streak Mode (5 Choices)")
        print("2. 📦 Focused SRS 5-Pack Mode (5 Choices)")
        print("0. ❌ Exit Program")
        print("-" * 45)
        
        choice = input("Select a option: ").strip()
        
        if choice == '1':
            play_endless(game_data)
        elif choice == '2':
            play_focused_packs(game_data)
        elif choice == '0':
            print("\nGoodbye! Keep practicing! 加油！")
            break
        else:
            print("\n⚠️ Invalid selection. Please type 1, 2, or 0.\n")

if __name__ == "__main__":
    main()