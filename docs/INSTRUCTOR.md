# Instructor notes

## Before the day

- [ ] Check the Fresh install badge on the README is green (Windows, macOS and Linux from scratch).
- [ ] Send participants the setup block from the Welcome page a few days before.
- [ ] The day before, run the workflow by hand (Actions → Fresh install → Run workflow), and run
      every notebook yourself: `uv run python tests/run_notebook.py`.
- [ ] Keep `dist/wardheat-datapack.zip` on a USB stick for anyone stuck on the Wi-Fi (unzip into `data/`).

## On the day

- Teach from the charts. Ask the question first ("where do you think it's hottest?"), then let people
  play with the chart before you explain.
- The Welcome page ends with setup and a check cell. Give people the first half hour for it.
- Only lesson 1 reads satellite data live (one search, one image). Demo it on the projector if the Wi-Fi
  is weak; everything after it reads small prepared files (~40 MB in all) that download on first use.
- Under each chart built from a prepared file, "How this file was made" folds out the code and what
  making it from scratch downloads. Open one in lesson 1 to show nothing is hidden.
- Each lesson ends with "Try it" prompts, each with a ready-made cell to edit, about ten minutes in total. Cut those before cutting the charts.
- Lesson 4's live forecast is usually Green outside March–May; the 2024 season in the calendar carries the story.

## Points that land

- **By day, the countryside is hotter than the city** (lesson 1). Ask before you toggle to night.
- **About 0.7 °C cooler per 10 % more canopy** (lesson 2). People remember and quote it.
- **Weights are a choice** (lesson 3). Let the room argue about the sliders.
- **40 °C never comes** (lesson 4). Bengaluru's hottest day since 1991 was 37.3 °C, so warnings must be local.

## Say out loud

- Surface temperature ≠ air temperature.
- Population is modelled; canopy is from 2018–20.
- Thresholds are not calibrated with health data yet.
- A risk map shows where to look first. Check it on the ground before acting on it.
