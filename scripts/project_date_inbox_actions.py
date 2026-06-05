import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen


PROJECT_OWNER = os.getenv("PROJECT_OWNER", "CeHePe")
PROJECT_NUMBER = int(os.getenv("PROJECT_NUMBER", "1"))
ASSIGNEE = os.getenv("ISSUE_ASSIGNEE", PROJECT_OWNER)
MENTION = os.getenv("DUE_DATE_MENTION", f"@{PROJECT_OWNER}")
PROJECT_URL = f"https://github.com/users/{PROJECT_OWNER}/projects/{PROJECT_NUMBER}"
SHANGHAI_TZ = timezone(timedelta(hours=8))


def target_date() -> str:
    override = os.getenv("REMINDER_DATE")
    if override:
        return override
    return datetime.now(SHANGHAI_TZ).date().isoformat()


def dry_run() -> bool:
    return os.getenv("DRY_RUN", "false").lower() == "true"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def request_json(url: str, token: str, *, method: str = "GET", data: dict | None = None) -> dict | list:
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub request failed: {method} {url}: {exc.code} {detail}") from exc


def graphql(query: str, variables: dict) -> dict:
    token = require_env("PROJECT_TOKEN")
    payload = request_json(
        "https://api.github.com/graphql",
        token,
        method="POST",
        data={"query": query, "variables": variables},
    )
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {json.dumps(payload['errors'])}")
    return payload["data"]


def fetch_project_items() -> list[dict]:
    query = """
    query($owner: String!, $number: Int!, $cursor: String) {
      user(login: $owner) {
        projectV2(number: $number) {
          items(first: 100, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              content {
                __typename
                ... on Issue {
                  number
                  title
                  url
                  state
                  repository {
                    owner {
                      login
                    }
                    name
                  }
                }
              }
              fieldValues(first: 30) {
                nodes {
                  __typename
                  ... on ProjectV2ItemFieldDateValue {
                    date
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                      }
                    }
                  }
                  ... on ProjectV2ItemFieldSingleSelectValue {
                    name
                    field {
                      ... on ProjectV2FieldCommon {
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    items = []
    cursor = None
    while True:
        data = graphql(query, {"owner": PROJECT_OWNER, "number": PROJECT_NUMBER, "cursor": cursor})
        page = data["user"]["projectV2"]["items"]
        items.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return items
        cursor = page["pageInfo"]["endCursor"]


def project_fields(item: dict) -> dict:
    values = {}
    for node in item["fieldValues"]["nodes"]:
        field = node.get("field")
        if not field:
            continue
        name = field.get("name")
        if node["__typename"] == "ProjectV2ItemFieldDateValue":
            values[name] = node.get("date")
        elif node["__typename"] == "ProjectV2ItemFieldSingleSelectValue":
            values[name] = node.get("name")
    return values


def actionable_issues(items: list[dict], date_text: str) -> list[dict]:
    actions = []
    for item in items:
        content = item.get("content")
        if not content or content.get("__typename") != "Issue":
            continue
        if content.get("state") != "OPEN":
            continue

        fields = project_fields(item)
        if fields.get("Status") == "Done":
            continue

        start_date = fields.get("Start date")
        due_date = fields.get("Due Date")
        if start_date != date_text and due_date != date_text:
            continue

        issue = {
            "number": content["number"],
            "title": content["title"],
            "url": content["url"],
            "repo_owner": content["repository"]["owner"]["login"],
            "repo_name": content["repository"]["name"],
            "start_date": start_date,
            "due_date": due_date,
            "status": fields.get("Status") or "No status",
        }
        if start_date == date_text:
            actions.append({**issue, "action": "assign"})
        if due_date == date_text:
            actions.append({**issue, "action": "comment"})
    return sorted(actions, key=lambda action: (action["number"], action["action"]))


def issue_api_url(action: dict, path: str) -> str:
    return f"https://api.github.com/repos/{action['repo_owner']}/{action['repo_name']}/issues/{action['number']}{path}"


def assign_issue(action: dict) -> None:
    if dry_run():
        print(f"DRY RUN assign #{action['number']} to {ASSIGNEE}")
        return
    request_json(
        issue_api_url(action, "/assignees"),
        require_env("ISSUE_TOKEN"),
        method="POST",
        data={"assignees": [ASSIGNEE]},
    )
    print(f"Assigned #{action['number']} to {ASSIGNEE}")


def existing_due_comment(action: dict, date_text: str) -> bool:
    marker = due_marker(action, date_text)
    comments = request_json(issue_api_url(action, "/comments?per_page=100"), require_env("ISSUE_TOKEN"))
    return any(marker in comment.get("body", "") for comment in comments)


def due_marker(action: dict, date_text: str) -> str:
    return f"<!-- project-date-reminder:due:{date_text}:issue:{action['number']} -->"


def comment_due_issue(action: dict, date_text: str) -> None:
    if existing_due_comment(action, date_text):
        print(f"Due-date comment already exists for #{action['number']} on {date_text}")
        return

    body = "\n".join(
        [
            due_marker(action, date_text),
            f"{MENTION} reminder: this issue is due today ({date_text}, Asia/Shanghai).",
            "",
            f"- Project: {PROJECT_URL}",
            f"- Status: {action['status']}",
            f"- Start date: {action['start_date'] or '-'}",
            f"- Due Date: {action['due_date'] or '-'}",
        ]
    )
    if dry_run():
        print(f"DRY RUN comment on #{action['number']}: {body}")
        return
    request_json(issue_api_url(action, "/comments"), require_env("ISSUE_TOKEN"), method="POST", data={"body": body})
    print(f"Commented due-date reminder on #{action['number']}")


def main() -> int:
    date_text = target_date()
    actions = actionable_issues(fetch_project_items(), date_text)
    if not actions:
        print(f"No Project issue actions for {date_text}.")
        return 0

    for action in actions:
        if action["action"] == "assign":
            assign_issue(action)
        elif action["action"] == "comment":
            comment_due_issue(action, date_text)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
