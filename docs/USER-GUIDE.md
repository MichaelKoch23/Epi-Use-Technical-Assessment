# User Guide

Employee Hierarchy Management System - a guide for the people who use it day to day.

This guide assumes no technical background. For how the system is built and why, see [TECHNICAL-DESIGN.md](TECHNICAL-DESIGN.md).

---

## Contents

1. [Signing in](#1-signing-in)
2. [What you can do depends on your role](#2-what-you-can-do-depends-on-your-role)
3. [Finding your way around](#3-finding-your-way-around)
4. [The org chart](#4-the-org-chart)
5. [The employee table](#5-the-employee-table)
6. [Employee details](#6-employee-details)
7. [Adding, editing and removing employees](#7-adding-editing-and-removing-employees)
8. [Changing who someone reports to](#8-changing-who-someone-reports-to)
9. [Time travel: past dates and planned changes](#9-time-travel-past-dates-and-planned-changes)
10. [Profile pictures and your profile page](#10-profile-pictures-and-your-profile-page)
11. [Exporting to a spreadsheet](#11-exporting-to-a-spreadsheet)
12. [Importing from a spreadsheet](#12-importing-from-a-spreadsheet)
13. [Analytics](#13-analytics)
14. [Change history](#14-change-history)
15. [Messages you might see](#15-messages-you-might-see)

---

## 1. Signing in

Open the application URL and enter your email address and password.

Two demo accounts are available:

| Account | Email | Role |
|---|---|---|
| Administrator | `admin@epiuse-demo.com` | `hr_admin` - full access |
| Read-only | `viewer@epiuse-demo.com` | `viewer` - can look, cannot change |

Passwords are supplied separately with the submission.

**If sign-in fails**, the message is deliberately the same whether the email is unknown or the password is wrong - this prevents anyone from using the login form to discover which email addresses have accounts. Check both.

**After several failed attempts in a row** the system will briefly refuse further tries. Wait a minute and try again.

**Signing out** uses the account menu at the top right. This ends the session on the server, not just in your browser, so the sign-in is not left usable on a shared or lost device.

---

## 2. What you can do depends on your role

| | Administrator (`hr_admin`) | Read-only (`viewer`) |
|---|---|---|
| Browse the org chart and employee table | ✓ | ✓ |
| See salaries | ✓ | ✗ |
| Add, edit, delete, restore employees | ✓ | ✗ |
| Change reporting lines | ✓ | ✗ |
| Export to CSV | ✓ (with salary) | ✓ (without salary) |
| Import a spreadsheet | ✓ | ✗ |
| View analytics | ✓ (including payroll cost) | ✓ (excluding payroll cost) |
| View change history | ✓ (including salary figures) | ✓ (figures hidden) |

If you are signed in as a viewer, buttons that would change data are simply not shown.

**A note on salaries.** For a read-only user, salary is not merely hidden in the interface - it is never sent to your browser at all. You will also find that sorting or filtering by salary is refused rather than silently ignored, because being able to ask "show me everyone earning over R500 000" would reveal the figures just as surely as displaying them.

---

## 3. Finding your way around

The bar across the top of every page contains:

- **Org chart**, **Employees**, **Analytics**, **Import** - the main sections.
- **Search** (magnifying glass) - jump to any person from anywhere. Keyboard shortcut: **Ctrl + K** (**⌘ + K** on a Mac). Start typing a name, an employee number or a job title; press **Enter** on a result to open that person.
- **Change history** (clock icon) - every change made in the system.
- **Account menu** (your picture, top right) - your signed-in identity, **Your profile**, and **Sign out**.

Signing in takes you to the org chart by default.

---

## 4. The org chart

A visual, interactive map of who reports to whom.

### Moving around

- **Drag the background** to pan.
- **Scroll** (or pinch) to zoom.
- Click the **+ / −** on a card to expand or collapse that person's reports. Large branches load as you open them, so the chart stays responsive even in a big organisation.

### Focus mode

Clicking a person enters **focus mode**: they and the levels beneath them stay bright while the rest of the organisation dims. This is the quickest way to read one department without the surrounding noise. Use the depth control to show more or fewer levels below the selected person, and **Exit focus** to return to the full view.

### Searching the chart

The search box on the chart finds a person and scrolls the chart to them, expanding whatever branches are needed to reveal them. This works even if they are deep inside a collapsed part of the tree.

### Viewing someone's details

Clicking a card opens a side panel with their details, their reporting line up to the top of the organisation, and - for administrators - buttons to edit, reassign or delete.

### Seeing the chart as at another date

The **Viewing as at** control above the chart redraws it as the organisation stood on any date you choose, and the **Scheduled changes** panel below it lists moves that have not yet taken effect. See [§9](#9-time-travel-past-dates-and-planned-changes).

### Saving a picture of the chart

**Export PNG** saves the current view as an image file, for slide decks or printing. What you see is what you get, so set up the view - focus, zoom, expanded branches - before exporting.

---

## 5. The employee table

A sortable, filterable list - the right tool when you want to compare people rather than see the shape of the organisation.

### Sorting

Click any column heading to sort by it. Click again to reverse the direction.

### Filtering

**Filters** opens a panel where you can narrow by:

- **Name** - partial matches are fine.
- **Position** - pick from a list of every job title currently in use.
- **Manager** - the list opens on the managers that the people you have already narrowed to actually report to, so after picking a position you are choosing between a handful of relevant names rather than hunting through the whole company. Typing still searches everyone.
- **Salary range** (administrators only)
- **Date of birth range**

A range whose minimum is above its maximum can never match anybody, so **Apply filters** stays disabled and tells you which way round it should be, rather than showing you an empty table.

Active filters appear as removable chips above the table; click the **×** on one to drop just that filter, or **Clear all** to reset.

### Deleted employees

A **Deleted** toggle lists people who have been removed. Deletion in this system is reversible - nothing is erased - so anyone here can be restored. See [§7](#7-adding-editing-and-removing-employees).

### Your view is shareable

The filters, sort order and page you are looking at are all recorded in the browser's address bar. Copying that URL and sending it to a colleague shows them exactly the same view, and your browser's Back button steps through your filtering as you would expect.

---

## 6. Employee details

Clicking a row in the table, or a card in the chart, opens that person's page:

- Their photograph, name, job title and employee number. Administrators can upload or change the photograph here ([§10](#10-profile-pictures-and-your-profile-page)).
- Date of birth, email address, and salary (administrators only).
- Their manager, and their direct reports.
- Their **reporting line** - the chain of managers from them to the top of the organisation.
- Their **assignment history** - every manager they have ever had, with the dates each arrangement started and ended, the reason recorded and who made the change ([§9](#9-time-travel-past-dates-and-planned-changes)).
- Their **change history** - every modification to this record, most recent first, with who made it and when.

---

## 7. Adding, editing and removing employees

*Administrators only.*

### Adding

**Add employee** on the employee table opens a form. Required: employee number, first and last name, email address, date of birth, position and salary. Optionally choose a manager - leave it empty for someone at the top of the organisation, such as the CEO.

Fields are checked as you type, so problems are flagged before you submit:

- Employee numbers and email addresses must be unique among active employees.
- A date of birth must be in the past.
- Salary cannot be negative.
- Currency is a three-letter code (`ZAR`, `USD`, …).

### Editing

**Edit** on an employee's page or row opens the same form, pre-filled.

If someone else changed that record while you had the form open, saving will stop and tell you so, rather than silently overwriting their work. Reopen the record to see the current values and re-apply your change.

### Deleting

**Delete** asks what should happen to that person's direct reports, and shows you exactly who is affected **before** you confirm:

| Option | Effect |
|---|---|
| **Reparent** *(default)* | Direct reports move up to the deleted person's own manager. The chain stays intact - usually what you want. |
| **Promote to root** | Direct reports become top-level, with no manager. |
| **Cascade delete** | The person **and everyone beneath them** are deleted. Use with care; the preview lists every affected person. |

### Restoring

Deletion is reversible. Turn on the **Deleted** toggle in the employee table, find the person and choose **Restore**.

One case to be aware of: if their employee number or email address was reassigned to someone else after they were deleted, restoring them would create a duplicate. The system refuses and tells you which identifier is taken; free it up, then restore.

---

## 8. Changing who someone reports to

*Administrators only.* There are three ways.

- **Drag and drop on the org chart.** Drag a person's card onto their new manager. Cards that cannot legally receive them are marked as you drag.
- **Reassign, from the chart's side panel.** Search for the new manager by name and select them. With a card selected on the chart, pressing **M** opens the same picker without reaching for the mouse.
- **Edit an employee**, and change the manager field.

### Two rules the system enforces

**Nobody can be their own manager**, and **reporting lines cannot form a loop** - if Thabo reports to Naledi, Naledi cannot be made to report to Thabo, directly or through anyone in between. Attempting it is refused with a message naming the chain that would have been created.

This is enforced by the database itself, not only by the interface, so it holds even if two people make conflicting changes at the same moment.

**Someone can have no manager.** That is how the CEO - or any top-level person - is represented. Leave the manager field empty.

### Every move is dated, and can be dated ahead

A reassignment is not a simple overwrite: it is recorded with the date it takes effect, which means it can be **scheduled for a future date** and the whole history stays readable. That is [§9](#9-time-travel-past-dates-and-planned-changes), and it is worth reading before you make your first change.

---

## 9. Time travel: past dates and planned changes

This is the part of the system most worth knowing about, because it changes what a reporting line *is*. A reassignment is not an overwrite. Every "who reports to whom" is recorded with the date it started and the date it ended, so the organisation can be read as it stood on any day - and a change can be decided now and take effect later, on its own.

### Viewing the organisation as at a past date

Above the org chart is a **Viewing as at** date box, with shortcuts for **Today**, **−3 months** and **−1 year**. Set a date and the whole chart redraws as the organisation stood that day - the reporting lines and everyone's place in the tree. A *future* date works too, and shows you the organisation as it will be once the changes scheduled before then have taken effect.

The date is kept in the address bar, so a historical view is a link you can send to someone.

While you are looking at any date other than today, a banner across the top says so, and **editing is switched off** - you cannot drag someone to a new manager in a view of March. This is deliberate: the most dangerous thing a historical view can do is look like the present one, and the second most dangerous is letting you act on it. Past views are amber, future views are teal, so the two are not mistaken for each other. **Return to today** on the banner, or **Today** on the date control, puts you back in the live view where editing works again.

If any changes are scheduled, **Jump to change** buttons appear next to the date box - one per date on which something happens - so you can step straight to the day the organisation next changes shape.

### Scheduling a change for a future date

When you reassign someone ([§8](#8-changing-who-someone-reports-to)), the confirmation dialog has an **Effective from** date, which defaults to today, and an optional **Reason**.

- **Leave the date as today** and the move happens immediately. The button reads **Confirm move**.
- **Set a future date** and the move is *scheduled*. The button changes to **Schedule move**, and the dialog tells you it takes effect on that date. Nothing changes in today's chart. On the morning of that date, the change becomes current by itself - there is no job to run and nobody has to remember.

A reason is worth filling in. It is stored with the change and shown in the person's assignment history, which is what turns "moved in March" into "moved in March, span-of-control rebalance".

### Before you commit: the move preview

Confirming a reassignment is not a blind action. The dialog first shows you exactly what the move does:

- **Who is affected** - the person and everyone beneath them, because a manager takes their branch with them.
- **Headcount** moving.
- **Depth change** - whether they end up higher, lower or at the same level.
- **Cost moving between branches** (administrators only) - the annual salary total leaving one branch and arriving in another.
- **Scheduled changes this will cancel** - see below.
- A **block**, if the move would create a reporting loop, naming the chain that would have formed.

The preview writes nothing. You can open it, read it and close it.

### Backdating a correction

You can set **Effective from** to a date in the *past*, which is how you correct a move that was recorded late. The one thing the system refuses is a date before that person's first recorded assignment, because there is no organisation to place them into before they existed in it.

### The scheduled changes panel

Below the chart, **Scheduled changes** lists every future-dated move that has not yet taken effect: who moves, to whom, on what date, why, and who decided it. Administrators can **cancel** any of them with the **×**. Cancelling puts things back as they were - the arrangement the scheduled change was going to replace simply continues.

**One scheduled change per person per date supersedes another.** If someone already has a move scheduled and you schedule a different one from the same date onward, the new decision replaces the old. The system does not do this quietly: the preview lists what will be cancelled before you confirm, and the confirmation tells you what was.

### One person's history

An employee's detail page has an **assignment history** - every manager they have had, each with its start date, its end date, the reason recorded, and who made the change. The run in force today is marked as current; anything not yet started is marked as scheduled.

### What does *not* travel in time

Only reporting lines are dated. Names, positions, salaries and who has been deleted are single current values, so a chart read at a past date shows **today's** people arranged in **that date's** reporting structure. Someone hired last week appears in a chart dated last year. This is a known limit rather than a bug, and it is worth remembering before treating a historical view as a historical record.

---

## 10. Profile pictures and your profile page

Everyone's picture is chosen in this order - the first one that exists is shown:

1. **An uploaded photo.**
2. **Their [Gravatar](https://gravatar.com)** - a free service that links a picture to an email address. A person who registers their **work email address** at gravatar.com and adds an image there appears with it here automatically.
3. **Their initials**, when there is no picture.

### Uploading a photo for an employee

*Administrators only.* Open the employee's page and click **Upload photo** (or click the picture itself). Choose a JPEG, PNG, WebP or GIF of up to 5 MB. The photo is cropped to a square and appears everywhere that person is shown - the table, the org chart and search. **Change photo** replaces it and **Remove** goes back to their Gravatar or initials.

A photo change is recorded in the employee's change history like any other edit.

An administrator can instead point to an image elsewhere on the web by entering its address in the **Avatar URL** field when editing an employee. The address must begin with `http://` or `https://`.

### Your profile page

Choose **Your profile** from the account menu. It shows:

- **Your picture**, with **Upload photo** / **Change photo** / **Remove**. Any signed-in user can change their own picture.
- **Profile picture** - which of the three sources above is currently in use, and whether a Gravatar exists for your email address (with a link to create one if not).
- **Access** - your role and what it allows you to do.
- **Your employee record** - if an employee has the same email address as your account, their job title, employee number, manager and direct reports are shown, each linking to that person's page.

---

## 11. Exporting to a spreadsheet

**Export CSV** on the employee table downloads the list as a file you can open in Excel, LibreOffice or Google Sheets.

Two things worth knowing:

- **The export honours your current filters and sort order.** Filter to one department first and you will export only that department. Clear the filters to export everyone.
- **Administrators get a salary column; read-only users do not.**

Managers are identified by **employee number** rather than by an internal identifier, which makes the exported file safe to edit and import straight back in ([§12](#12-importing-from-a-spreadsheet)).

---

## 12. Importing from a spreadsheet

*Administrators only.* Use **Import** to create or update many employees at once, from a `.csv` or `.xlsx` file.

### Preparing the file

The first row must be column headings. The columns are:

| Column | Required | Notes |
|---|---|---|
| `employee_number` | Yes | The key. Matches an existing employee → updates them. New → creates them. |
| `first_name` | Yes | |
| `last_name` | Yes | |
| `email` | Yes | Must be unique among active employees |
| `birth_date` | Yes | `YYYY-MM-DD`, e.g. `1990-04-27` |
| `position` | Yes | |
| `salary` | Yes | A number, e.g. `450000` or `450000.50`; at most two decimal places |
| `currency` | No | Three letters; defaults to `ZAR` |
| `manager_employee_number` | No | The manager's **employee number**, not their name |

The simplest way to start is to **export first** ([§11](#11-exporting-to-a-spreadsheet)) and edit the file you get back - the columns already match.

To make someone top-level, leave `manager_employee_number` empty. This is treated as an instruction ("reports to nobody"), so it will clear an existing manager.

### Importing

1. Choose your file. The system checks it immediately and shows a **preview** - every row marked as *will create*, *will update*, or *blocked* with the reason.
2. Review the preview. Nothing has been written at this stage.
3. If you are satisfied, confirm the import.

### All-or-nothing

**If any row is blocked, nothing is imported.** A half-applied import is worse than none, because you cannot easily tell what landed. Fix the reported rows and try again.

Rows are blocked for reasons such as: a missing required field, an unreadable date, an employee number or email appearing twice in the file, an email already belonging to someone else, a manager who is in neither the file nor the system, a date of birth in the future, or a set of reporting lines that would create a loop.

A row is also blocked if a value breaks one of the same limits the **Add employee** form applies - a name longer than 100 characters, a currency that is not three letters, an address that is not a valid email, a salary that is impossibly large, a date of birth before 1900. A spreadsheet is checked exactly as strictly as the form is, so an import cannot put anything into the system that you could not have typed in.

The row numbers match what you see in your spreadsheet program, so they are easy to find.

---

## 13. Analytics

A dashboard describing the shape of the organisation.

- **Headcount**, number of top-level people, managers and individual contributors.
- **Span of control** - how many people managers have reporting to them, on average and as a distribution.
- **Depth** - how many layers the organisation has, and how people are spread across them.
- **Payroll cost** - total, average and median salary. *Administrators only.*
- **Anomalies** - things worth a look rather than errors:
  - *Wide spans* - managers with an unusually large number of direct reports.
  - *Single-report managers* - managers with exactly one report, often a sign of an unnecessary layer.
  - *Deep chains* - people a long way from the top.
  - *Unreachable* - active employees not connected to any top-level person. This should normally be empty; if it is not, someone's manager has been removed without their reports being moved, and they will be missing from the org chart.

**Branch explorer** shows the same figures for one department: pick a person and see the totals for everyone beneath them.

**Compare two dates** answers "what actually changed?" between any two dates. Pick a **from** and a **to** date and it reports who changed manager, which of those were whole-branch moves, who became or stopped being top-level, how the maximum depth and the average span of control shifted, and - for administrators - the total salary that moved between branches. This reads the same dated reporting records as [§9](#9-time-travel-past-dates-and-planned-changes), so it needs no separate change log and cannot disagree with one.

---

## 14. Change history

The clock icon in the top bar opens a record of **every** change made in the system: who made it, what they changed, and when. Individual employees have the same view, filtered to their own record, on their detail page.

Each entry shows the before and after values. Read-only users see that a salary changed without seeing the figures.

The history is written as part of the change itself, so it cannot disagree with the data - a change can never be made without being recorded.

---

## 15. Messages you might see

| Message | What it means | What to do |
|---|---|---|
| *Incorrect email or password* | Either the email is not registered or the password is wrong | Check both; the message is intentionally the same for either |
| *Too many login attempts* | Several failed sign-ins in quick succession | Wait a minute |
| *The record changed since it was last read* | Someone else edited this record while your form was open | Close and reopen the record, then re-apply your change |
| *Employee number / Email is already in use* | Another active employee holds it | Choose a different one, or free it on the other record |
| *Would create a reporting cycle* | The reassignment would make a loop | Pick a manager who is not below this person |
| *This employee and their entire subtree are deleted* | You have selected **Cascade** | Check the preview list; choose **Reparent** if you did not mean it |
| *Effective date precedes the first recorded assignment* | You backdated a move to before this person had any reporting line at all | Choose a date on or after their first recorded assignment - their assignment history shows it |
| *The assignment is already in force* | You tried to cancel a scheduled change that has since taken effect | It is history now; reassign them again if you want it undone |
| *Import file exceeds the … limit* | The upload is too large | Split it into smaller files |
| *File is not a readable .xlsx workbook* | The file is corrupt, or not really a spreadsheet | Re-export it from your spreadsheet program |
| Session ends unexpectedly | Your sign-in expired, or was signed out elsewhere | Sign in again |

---

## Getting help

For anything not covered here, or behaviour that looks wrong, please include what you were doing, what you expected, and what happened instead. If a specific record is involved, its employee number helps considerably.
