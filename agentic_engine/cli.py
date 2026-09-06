import argparse

from .engine import Orchestrator


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--new-chat", action="store_true")
    parser.add_argument("--chat-id", type=str)
    parser.add_argument("--message", type=str, required=True)
    parser.add_argument("--file", type=str)

    args = parser.parse_args()

    engine = Orchestrator()

    # Create a new chat
    if args.new_chat:
        chat_id = engine.new_chat()
        print(f"NEW CHAT: {chat_id}")

    # Continue an existing chat
    elif args.chat_id:
        chat_id = args.chat_id
        print(f"CONTINUING CHAT: {chat_id}")

    else:
        parser.error("Use either --new-chat or --chat-id")

    result = engine.run(
        chat_id=chat_id,
        user_text=args.message,
        file_path=args.file,
    )

    print("\n========================================")
    print("RESULT")
    print("========================================")
    print(f"TASK      : {result.get('task')}")
    print(f"COMPLEXITY: {result.get('complexity')}")
    print(f"MODEL     : {result.get('model')}")
    print(f"STATUS    : {result.get('status')}")

    print("\nANSWER")
    print("----------------------------------------")
    print(result.get("answer", ""))

    if result.get("output_file"):
        print("\nOUTPUT FILE:")
        print(result["output_file"])


if __name__ == "__main__":
    main()