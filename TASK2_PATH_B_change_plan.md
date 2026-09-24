# Task 2 – Specialization Path B: User Onboarding & Change Management Plan

How the engineering team should adopt this automated audit tool into their
daily code review workflow:

1. **Start as an extra check, not a replacement.** Run the audit tool
   alongside normal human code review for the first few weeks, rather than
   instead of it. This lets the team build trust in what the AI catches (and
   what it misses) before relying on it more heavily, and avoids the risk of
   a wrong AI call slipping through unquestioned.

2. **Wire it into the pull request process.** Once the team is comfortable
   with it, run the audit automatically whenever a pull request is opened,
   and require any "Critical" severity finding to be resolved or explicitly
   acknowledged before the code can be merged. This turns the tool from
   something people have to remember to run into something that happens
   automatically, which is the only way these tools actually get used
   consistently long-term.

3. **Review and tune it monthly.** In the first month, have a tech lead
   quickly review a sample of the audit's findings to check for false
   positives or missed patterns, and adjust the prompt or rules based on what
   they see. AI audit quality drifts over time as the codebase and coding
   patterns change, so this can't be a "set it up once and forget it" tool.
