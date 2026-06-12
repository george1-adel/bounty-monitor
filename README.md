# Bug Bounty Monitor Bot

A Telegram bot that automatically tracks new bug bounty programs and scope changes across major platforms. It checks for updates every 15 minutes and sends instant notifications to all subscribers.

**Bot:** [@George0bot](https://t.me/George0bot)

---

## What It Does

- Monitors five major bug bounty platforms for changes
- Detects when a new program is launched
- Detects when new scopes (targets) are added to existing programs
- Identifies programs that were previously private and have gone public
- Sends structured notifications to all Telegram subscribers

## Platforms Monitored

| Platform   | Source                        |
|------------|-------------------------------|
| HackerOne  | bounty-targets-data (GitHub)  |
| Bugcrowd   | bounty-targets-data (GitHub)  |
| Intigriti  | bounty-targets-data (GitHub)  |
| YesWeHack  | bounty-targets-data (GitHub)  |
| Federacy   | bounty-targets-data (GitHub)  |

Data is sourced from [arkadiyt/bounty-targets-data](https://github.com/arkadiyt/bounty-targets-data), which aggregates public program data from all major platforms.

## How It Works

1. A GitHub Actions workflow runs on a 15-minute cron schedule
2. The script fetches the latest program data from all platforms
3. It compares the current data against the previously saved state
4. If new programs or scopes are found, it broadcasts a notification to all Telegram subscribers
5. The updated data is committed back to this repository for persistence

## Notification Types

**New Program** — sent when a program appears for the first time in the public data. Includes program name, URL, bounty range, and all in-scope targets.

**Program Went Public** — sent when a previously private program is opened to the public. This is tracked using a separate private programs tracker file.

**New Scope Added** — sent when an existing program adds new in-scope targets. Only the newly added scopes are listed.

## Usage

Send `/start` to [@George0bot](https://t.me/George0bot) on Telegram to subscribe. You will begin receiving notifications within the next check cycle (up to 15 minutes).

Send `/stop` to unsubscribe.

## Project Structure

```
monitor_action.py                 # Main monitoring script
bounty_data/
  subscribers.json                # List of subscribed Telegram chat IDs
  private_programs_tracker.json   # Tracks programs seen as private
  tg_offset.json                  # Telegram update offset for polling
  hackerone.json                  # Cached program data (HackerOne)
  bugcrowd.json                   # Cached program data (Bugcrowd)
  intigriti.json                  # Cached program data (Intigriti)
  yeswehack.json                  # Cached program data (YesWeHack)
  federacy.json                   # Cached program data (Federacy)
.github/workflows/
  monitor.yml                     # GitHub Actions cron workflow
```

## Requirements

- Python 3.11+
- `requests` library
- GitHub Actions (runs automatically, no server needed)

## License

This project is provided as-is for personal and educational use.
