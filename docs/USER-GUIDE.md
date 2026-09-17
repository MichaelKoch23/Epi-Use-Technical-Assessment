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
9. [Profile pictures and your profile page](#9-profile-pictures-and-your-profile-page)
10. [Exporting to a spreadsheet](#10-exporting-to-a-spreadsheet)
11. [Importing from a spreadsheet](#11-importing-from-a-spreadsheet)
12. [Analytics](#12-analytics)
13. [Change history](#13-change-history)
14. [Messages you might see](#14-messages-you-might-see)

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
- **Manager**
- **Salary range** (administrators only)
- **Date of birth range**

Active filters appear as removable chips above the table; click the **×** on one to drop just that filter, or **Clear all** to reset.

### Deleted employees

A **Deleted** toggle lists people who have been removed. Deletion in this system is reversible - nothing is erased - so anyone here can be restored. See [§7](#7-adding-editing-and-removing-employees).

### Your view is shareable

The filters, sort order and page you are looking at are all recorded in the browser's address bar. Copying that URL and sending it to a colleague shows them exactly the same view, and your browser's Back button steps through your filtering as you would expect.

---

## 6. Employee details

Clicking a row in the table, or a card in the chart, opens that person's page:

- Their photograph, name, job title and employee number. Administrators can upload or change the photograph here ([§9](#9-profile-pictures-and-your-profile-page)).
- Date of birth, email address, and salary (administrators only).
- Their manager, and their direct reports.
- Their **reporting line** - the chain of managers from them to the top of the organisation.
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
- **Reassign, from the chart's side panel.** Search for the new manager by name and select them.
- **Edit an employee**, and change the manager field.

### Two rules the system enforces

**Nobody can be their own manager**, and **reporting lines cannot form a loop** - if Thabo reports to Naledi, Naledi cannot be made to report to Thabo, directly or through anyone in between. Attempting it is refused with a message naming the chain that would have been created.

This is enforced by the database itself, not only by the interface, so it holds even if two people make conflicting changes at the same moment.

**Someone can have no manager.** That is how the CEO - or any top-level person - is represented. Leave the manager field empty.

---

## 9. Profile pictures and your profile page

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

## 10. Exporting to a spreadsheet

**Export CSV** on the employee table downloads the list as a file you can open in Excel, LibreOffice or Google Sheets.

Two things worth knowing:

- **The export honours your current filters and sort order.** Filter to one department first and you will export only that department. Clear the filters to export everyone.
- **Administrators get a salary column; read-only users do not.**

Managers are identified by **employee number** rather than by an internal identifier, which makes the exported file safe to edit and import straight back in ([§11](#11-importing-from-a-spreadsheet)).

---

## 11. Importing from a spreadsheet

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
| `salary` | Yes | Digits only, e.g. `450000` |
| `currency` | No | Three letters; defaults to `ZAR` |
| `manager_employee_number` | No | The manager's **employee number**, not their name |

The simplest way to start is to **export first** ([§10](#10-exporting-to-a-spreadsheet)) and edit the file you get back - the columns already match.

To make someone top-level, leave `manager_employee_number` empty. This is treated as an instruction ("reports to nobody"), so it will clear an existing manager.

### Importing

1. Choose your file. The system checks it immediately and shows a **preview** - every row marked as *will create*, *will update*, or *blocked* with the reason.
2. Review the preview. Nothing has been written at this stage.
3. If you are satisfied, confirm the import.

### All-or-nothing

**If any row is blocked, nothing is imported.** A half-applied import is worse than none, because you cannot easily tell what landed. Fix the reported rows and try again.

Rows are blocked for reasons such as: a missing required field, an unreadable date, an employee number or email appearing twice in the file, an email already belonging to someone else, a manager who is in neither the file nor the system, a date of birth in the future, or a set of reporting lines that would create a loop. The row numbers match what you see in your spreadsheet program, so they are easy to find.

---

## 12. Analytics

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

---

## 13. Change history

The clock icon in the top bar opens a record of **every** change made in the system: who made it, what they changed, and when. Individual employees have the same view, filtered to their own record, on their detail page.

Each entry shows the before and after values. Read-only users see that a salary changed without seeing the figures.

The history is written as part of the change itself, so it cannot disagree with the data - a change can never be made without being recorded.

---

## 14. Messages you might see

| Message | What it means | What to do |
|---|---|---|
| *Incorrect email or password* | Either the email is not registered or the password is wrong | Check both; the message is intentionally the same for either |
| *Too many login attempts* | Several failed sign-ins in quick succession | Wait a minute |
| *The record changed since it was last read* | Someone else edited this record while your form was open | Close and reopen the record, then re-apply your change |
| *Employee number / Email is already in use* | Another active employee holds it | Choose a different one, or free it on the other record |
| *Would create a reporting cycle* | The reassignment would make a loop | Pick a manager who is not below this person |
| *This employee and their entire subtree are deleted* | You have selected **Cascade** | Check the preview list; choose **Reparent** if you did not mean it |
| *Import file exceeds the … limit* | The upload is too large | Split it into smaller files |
| *File is not a readable .xlsx workbook* | The file is corrupt, or not really a spreadsheet | Re-export it from your spreadsheet program |
| Session ends unexpectedly | Your sign-in expired, or was signed out elsewhere | Sign in again |

---

## Getting help

For anything not covered here, or behaviour that looks wrong, please include what you were doing, what you expected, and what happened instead. If a specific record is involved, its employee number helps considerably.
