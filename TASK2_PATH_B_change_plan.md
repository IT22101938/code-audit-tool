# Task 2 – Path B (bonus): User Onboarding & Change Plan

How an engineering team can start using the audit tool in their daily code review:

1. **Start as an extra check, not a replacement.** For the first few weeks, run the tool next to normal human code review and only show its results as advice. This lets the team see what the AI catches and what it misses before they depend on it. Blocking merges starts after this trust period.

2. **Connect it to pull requests.** After the trust period, run the audit automatically on every pull request. A Critical finding must be fixed, or approved by a named person, before the code can merge. If the AI was down and the backup scanner ran, treat the result as "needs review" and never as a clean pass. Automatic runs are what make people actually use a tool.

3. **Review and tune it every month.** A tech lead checks a sample of findings each month for false alarms and missed problems, then adjusts the prompt or rules. Code and habits change over time, so the tool needs regular care.
