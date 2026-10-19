import sqlite3
import json
from datetime import datetime

def load_emails():
    emails = []
    with open("email_500.txt", "r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            sender, rest = line.split(": text:", 1)
            text, date = rest.split(": date:", 1)
            email = {
                "sender": sender.replace("from:", "").strip(),
                "text": text.strip(),
                "date": date.strip()
            }
            emails.append(email)
    return emails

def analyze_email(sender, text):
    text = text.lower()
    score = 0
    reasons = []
    spam_words = {
        "congratulations": 2,
        "you won": 3,
        "claim your prize": 3,
        "click here": 2,
        "free gift": 2,
        "guaranteed returns": 3,
        "verify your account": 2,
        "no credit check": 3,
        "bank details": 2,
        "act now": 2,
        "special bonus": 3,
        "confirm your details": 3,
        "limited-time offer": 2,
        "no experience needed": 2,
        "zero risk": 3,
        "urgent": 2,
        "pay the small delivery fee": 3,
        "update your payment information": 3
    }
    for word, points in spam_words.items():
        if word in text:
            score += points
            reasons.append("Підозрілий вираз: " + word)
    suspicious_domains = [
        "bonus-center.com",
        "lucky-mail.net",
        "profit-zone.net",
        "verify-alert.com"
    ]
    for domain in suspicious_domains:
        if domain in sender.lower():
            score += 2
            reasons.append("Підозрілий домен відправника")
            break
    if score >= 3:
        classification = "spam"
    else:
        classification = "not_spam"
    confidence = min(0.5 + abs(score - 3) * 0.1, 0.99)
    if not reasons:
        reasons.append("Підозрілих виразів не знайдено")
    return {
        "classification": classification,
        "confidence": round(confidence, 2),
        "reasons": reasons
    }

def improved_analyze_email(sender, text):
    result = analyze_email(sender, text)
    text = text.lower()
    score = 0
    reasons = []
    suspicious_actions = [
        "confirm your details",
        "verify your account",
        "submit your bank details",
        "update your payment information",
        "claim your prize",
        "guaranteed returns",
        "pay the small delivery fee",
        "confirm your address",
        "requires verification",
        "no credit check"
    ]
    for phrase in suspicious_actions:
        if phrase in text:
            score += 3
            reasons.append("Ризикована дія: " + phrase)
    urgent_words = [
        "urgent",
        "immediately",
        "within 24 hours",
        "act now",
        "expires tonight"
    ]
    for word in urgent_words:
        if word in text:
            score += 1
            reasons.append("Терміновість: " + word)
    normal_words = [
        "weekly meeting",
        "project plan",
        "lecture notes",
        "your invoice for this month",
        "monthly account statement",
        "your order has been shipped",
        "support ticket"
    ]
    for phrase in normal_words:
        if phrase in text:
            score -= 2
            reasons.append("Звичайний контекст: " + phrase)
    if result["classification"] == "spam":
        score += 2
    if score >= 3:
        classification = "spam"
    else:
        classification = "not_spam"
    confidence = min(0.5 + abs(score - 3) * 0.1, 0.99)
    if not reasons:
        reasons.append("Явних додаткових ознак не знайдено")
    return {
        "classification": classification,
        "confidence": round(confidence, 2),
        "reasons": reasons
    }

def compare_ai():
    emails = load_emails()
    old_spam = 0
    new_spam = 0
    changes = 0
    for email in emails:
        old = analyze_email(email["sender"], email["text"])
        new = improved_analyze_email(email["sender"], email["text"])
        if old["classification"] == "spam":
            old_spam += 1
        if new["classification"] == "spam":
            new_spam += 1
        if old["classification"] != new["classification"]:
            changes += 1
    print("\n     AI COMPARISON")
    print("Total emails:", len(emails))
    print("\nOriginal AI:")
    print("Spam:", old_spam)
    print("Not spam:", len(emails) - old_spam)
    print("\nImproved AI:")
    print("Spam:", new_spam)
    print("Not spam:", len(emails) - new_spam)
    print("\nChanged classifications:", changes)
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender, text, user_classification
        FROM emails
        WHERE user_classification IS NOT NULL
    """)
    checked_emails = cursor.fetchall()
    conn.close()
    old_correct = 0
    new_correct = 0
    for sender, text, correct_answer in checked_emails:
        old = analyze_email(sender, text)
        new = improved_analyze_email(sender, text)
        if old["classification"] == correct_answer:
            old_correct += 1
        if new["classification"] == correct_answer:
            new_correct += 1
    if checked_emails:
        total = len(checked_emails)
        print("\nAccuracy comparison:")
        print(f"Original AI: {old_correct / total * 100:.1f}%")
        print(f"Improved AI: {new_correct / total * 100:.1f}%")
    else:
        print("\nНемає оцінених повідомлень для порівняння.")


def create_database():
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            text TEXT,
            date TEXT,
            classification TEXT,
            confidence REAL,
            reasons TEXT,
            created_at TEXT,
            ai_classification TEXT,
            user_classification TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_email(email, result, show_message=True):
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO emails (
            sender, text, date, classification,
            confidence, reasons, created_at,
            ai_classification
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        email["sender"],
        email["text"],
        email["date"],
        result["classification"],
        result["confidence"],
        json.dumps(result["reasons"], ensure_ascii=False),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        result["classification"]
    ))
    conn.commit()
    email_id = cursor.lastrowid
    conn.close()
    if show_message:
        print("\nРезультат збережено в базі даних!")
    return email_id

def get_feedback(email_id, ai_result):
    print("\nПравильна класифікація?")
    print("1. Так")
    print("2. Ні")
    print("0. Пропустити")
    choice = input("Ваш вибір: ")
    if choice == "1":
        user_classification = ai_result
    elif choice == "2":
        print("\nВкажіть правильну класифікацію:")
        print("1. SPAM")
        print("2. NOT SPAM")
        answer = input("Ваш вибір: ")
        if answer == "1":
            user_classification = "spam"
        elif answer == "2":
            user_classification = "not_spam"
        else:
            print("Невірний вибір!")
            return
    else:
        print("Оцінку пропущено.")
        return
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE emails
        SET user_classification = ?
        WHERE id = ?
    """, (user_classification, email_id))
    conn.commit()
    conn.close()
    print("\nОцінку користувача збережено!")

def check_email():
    print("\n      EMAIL CHECK")
    sender = input("From: ")
    text = input("Text: ")
    email = {
        "sender": sender,
        "text": text,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    result = analyze_email(sender, text)
    print("\n      AI RESULT")
    print("Classification:", result["classification"].upper())
    print("Confidence:", f"{result['confidence'] * 100:.0f}%")
    print("\nПричини:")
    for reason in result["reasons"]:
        print("-", reason)
    email_id = save_email(email, result)
    get_feedback(email_id, result["classification"])

def analyze_file():
    emails = load_emails()
    spam = 0
    not_spam = 0
    total_confidence = 0
    added = 0
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    for email in emails:
        # Проверяем, есть ли уже такое письмо
        cursor.execute("""
            SELECT id FROM emails
            WHERE sender = ? AND text = ? AND date = ?
        """, (email["sender"], email["text"], email["date"]))
        if cursor.fetchone():
            continue
        result = analyze_email(email["sender"], email["text"])
        if result["classification"] == "spam":
            spam += 1
        else:
            not_spam += 1
        total_confidence += result["confidence"]
        save_email(email, result, False)
        added += 1
    conn.close()
    print("\n     ANALYSIS REPORT")
    print("Emails in file:", len(emails))
    print("Processed:", added)
    print("Skipped duplicates:", len(emails) - added)
    print("Spam:", spam)
    print("Not spam:", not_spam)
    if added > 0:
        average = total_confidence / added * 100
        print(f"Average confidence: {average:.1f}%")
    print("\nАналіз завершено!")

def show_history():
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sender, classification, confidence
        FROM emails
        ORDER BY id DESC
        LIMIT 20
    """)
    emails = cursor.fetchall()
    print("\n     EMAIL HISTORY")
    if not emails:
        print("Історія порожня.")
    for email in emails:
        print(f"\nID: {email[0]}")
        print("From:", email[1])
        print("Classification:", email[2].upper())
        print(f"Confidence: {email[3] * 100:.0f}%")
        print("-" * 35)
    email_id = input("\nВведіть ID для перегляду (0 - назад): ")
    if email_id.isdigit() and email_id != "0":
        cursor.execute(
            "SELECT * FROM emails WHERE id = ?", (int(email_id),)
        )
        email = cursor.fetchone()
        if email:
            print("\n     EMAIL DETAILS")
            print("From:", email[1])
            print("Text:", email[2])
            print("Date:", email[3])
            print("Classification:", email[4].upper())
            print(f"Confidence: {email[5] * 100:.0f}%")
            print("\nПричини:")
            for reason in json.loads(email[6]):
                print("-", reason)
            print("\nAI:", email[8])
            print("User:", email[9] or "Не перевірено")
        else:
            print("Повідомлення не знайдено!")
    conn.close()

def show_statistics():
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM emails")
    total = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM emails
        WHERE user_classification IS NOT NULL
    """)
    checked = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM emails
        WHERE ai_classification = user_classification
    """)
    correct = cursor.fetchone()[0]
    incorrect = checked - correct
    cursor.execute("""
        SELECT COUNT(*) FROM emails
        WHERE ai_classification = 'spam'
        AND user_classification = 'not_spam'
    """)
    false_spam = cursor.fetchone()[0]
    cursor.execute("""
        SELECT COUNT(*) FROM emails
        WHERE ai_classification = 'not_spam'
        AND user_classification = 'spam'
    """)
    missed_spam = cursor.fetchone()[0]
    conn.close()
    accuracy = correct / checked * 100 if checked > 0 else 0
    print("\n     STATISTICS")
    print("Total:", total)
    print("Checked by user:", checked)
    print("Correct:", correct)
    print("Incorrect:", incorrect)
    if checked > 0:
        print(f"Accuracy: {accuracy:.1f}%")
    else:
        print("Accuracy: немає оцінених повідомлень")
    print("\nAI → SPAM | User → NOT SPAM:", false_spam)
    print("AI → NOT SPAM | User → SPAM:", missed_spam)

def analyze_errors():
    conn = sqlite3.connect("spam_filter.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sender, text, ai_classification,
               user_classification, reasons
        FROM emails
        WHERE user_classification IS NOT NULL
        AND ai_classification != user_classification
    """)
    errors = cursor.fetchall()
    conn.close()
    print("\n     AI ERROR ANALYSIS")
    if not errors:
        print("Помилок AI поки не знайдено.")
        return
    print("Кількість помилок:", len(errors))
    false_spam = 0
    missed_spam = 0
    common_reasons = {}
    for sender, text, ai, user, reasons in errors:
        if ai == "spam":
            false_spam += 1
        else:
            missed_spam += 1
        for reason in json.loads(reasons):
            common_reasons[reason] = common_reasons.get(reason, 0) + 1
    print("\nТипи помилок:")
    print("Звичайні листи визначені як SPAM:", false_spam)
    print("Спам визначений як NOT SPAM:", missed_spam)
    print("\nОзнаки, пов'язані з помилками:")
    for reason, count in sorted(
        common_reasons.items(),
        key=lambda item: item[1],
        reverse=True
    )[:5]:
        print(f"- {reason}: {count}")
    print("\nРекомендації:")
    if false_spam > 0:
        print("- Враховувати контекст повідомлення,")
        print("  а не лише окремі підозрілі слова.")
    if missed_spam > 0:
        print("- Додати ознаки шахрайських пропозицій")
        print("  та перевірки особистих даних.")
    print("- Не вважати слова payment, invoice,")
    print("  account автоматично ознаками спаму.")

def show_menu():
    print("\n        AI SPAM FILTER\n")
    print("1. Перевірити email")
    print("2. Проаналізувати файл")
    print("3. Переглянути історію")
    print("4. Статистика")
    print("5. Перевірити помилки AI")
    print("6. Порівняти версії AI")
    print("0. Вихід")



create_database()
while True:
    show_menu()
    choice = input("\nОберіть дію: ")
    if choice == "1":
        check_email()
    elif choice == "2":
        analyze_file()
    elif choice == "3":
        show_history()
    elif choice == "4":
        show_statistics()
    elif choice == "5":
        analyze_errors()
    elif choice == "6":
        compare_ai()
    elif choice == "0":
        print("\nДо побачення!")
        break
    else:
        print("\nНевірний вибір. Спробуйте ще раз.")
