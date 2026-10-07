# LEAP — Production-Grade UI/UX Redesign Prompt

Historical design brief, not the current implementation specification. See
[the project structure](../project-structure.md) and [current status](../status.md)
for the maintained architecture and implemented behavior. Paths below may describe
the pre-reorganization layout.

You are a **senior product designer, UX architect, and frontend engineer** with experience building production-grade products similar to **Duolingo, Brilliant, Khan Academy, Coursera, Linear, Notion, and modern AI-native SaaS applications**.

Your task is to design and implement the frontend for **LEAP**, an adaptive learning platform for learning Artificial Intelligence and Machine Learning.

The final product must feel like a **real funded startup product**, not a hackathon project, academic dashboard, generic LMS, or AI-generated template.

---

## 1. Product Context

**LEAP** is an interactive learning platform that teaches machine learning concepts through structured, progressive learning experiences.

A learner may select tasks such as:

* Sentiment Analysis
* Image Classification
* Regression
* Other ML/AI tasks in the future

Each learning task contains:

* Multiple stages
* Multiple steps within each stage
* Educational content
* Examples
* Interactive questions
* Exercises
* Immediate feedback
* Retry / alternative-question functionality
* Progress tracking
* Concept mastery tracking

Users should generally need to demonstrate understanding before progressing.

LEAP should therefore feel like a combination of:

> **Brilliant-style active learning + Duolingo-style progression + Linear-quality interface design + an AI-native educational product**

---

## 2. Primary Design Goal

Design LEAP so that when someone opens the product they immediately think:

> "This looks like a polished production platform that a serious EdTech/AI startup built."

The UI should be:

* Premium
* Clean
* Modern
* Intelligent
* Highly readable
* Visually cohesive
* Interactive
* Focused
* Responsive
* Accessible
* Fast
* Delightful without being childish

Avoid making it overly corporate, overly academic, or overly gamified.

---

## 3. Design Philosophy

### Clarity over decoration

Every visual element must serve a purpose.

### Learning content is the hero

The interface should never compete with the educational material.

### Progressive disclosure

Do not overwhelm learners with everything at once.

### Strong hierarchy

A user should immediately understand:

1. What they are learning
2. Where they currently are
3. What they need to do
4. What happens next

### Calm visual environment

Use whitespace, typography, subtle surfaces, and restrained color.

### Modern AI-native feel

The platform should feel contemporary, but avoid clichéd UI patterns such as:

* Glowing purple gradients everywhere
* Excessive glassmorphism
* Neon cyberpunk styling
* Random AI sparkles
* Giant gradient headlines
* Generic SaaS landing-page aesthetics

### Desktop-first learning experience

Optimize the primary learning experience for a MacBook-sized display while remaining fully responsive on tablets and mobile devices.

---

## 4. Visual Direction

Use a visual language inspired by the refinement of products such as:

* Linear
* Notion
* Vercel
* Raycast
* Arc
* Brilliant
* Duolingo
* Khan Academy
* Stripe

Do **not** directly copy any product.

Create a unique visual identity for LEAP.

### Background

Use a subtle neutral application background rather than pure white everywhere.

Good options include:

* Off-white
* Warm gray
* Cool gray
* Light slate

Use elevated white or near-white surfaces for important content.

### Cards

Cards should use:

* Subtle borders
* Restrained shadows where needed
* Medium corner radius
* Generous padding

Avoid placing every section inside a floating card.

### Color

Use one distinctive **LEAP primary accent color**.

Use supporting semantic colors for:

* Success
* Warning
* Error
* Information
* Active learning states

Keep colors slightly muted and sophisticated.

Avoid rainbow dashboards.

### Typography

Typography is extremely important.

Use a modern sans-serif font such as:

* Inter
* Geist
* Manrope
* Or another high-quality system/UI font

Use:

* Strong heading hierarchy
* Comfortable reading line-height
* Restrained font weights
* Readable paragraph widths
* Excellent code typography

Educational content must be extremely easy to scan.

---

## 5. Application Structure

Create a coherent application shell.

### Left Navigation

Use a compact collapsible sidebar containing:

* LEAP logo / wordmark
* Dashboard
* Learn
* My Progress
* Tasks / Courses
* Achievements, only if useful
* Settings
* User profile

Do not make the sidebar unnecessarily wide.

### Top Area

Depending on the page, include:

* Breadcrumbs
* Page title
* Task title
* Stage
* Progress
* Contextual actions

Avoid redundant navigation bars.

---

## 6. Dashboard

The dashboard should immediately answer:

> **"What should I do next?"**

### Continue Learning

This should be the most visually prominent section.

Show:

* Current task
* Current stage
* Current step
* Progress percentage
* Estimated remaining content, if available
* Primary Continue CTA

Example:

```text
Sentiment Analysis
Stage 3 of 6 · Neural Networks
Step 4 of 6

[Continue Learning →]
```

### Learning Tasks

Display available learning tasks with meaningful visual differentiation.

Each task can contain:

* Task name
* Short description
* Difficulty
* Progress
* Completion state
* Concepts covered
* Primary CTA

Do not make the cards look like generic Bootstrap cards.

### Progress Overview

Show meaningful learning metrics such as:

* Concepts mastered
* Stages completed
* Exercises answered
* Accuracy
* Learning streak, only if useful

Focus on educational value rather than vanity metrics.

### Recent Activity

Display recent learning progress using a restrained timeline or list.

---

## 7. Core Learning Experience

This is the **most important page in the entire product**.

Spend the most design effort here.

The page should keep the learner focused while making progress visible at all times.

A possible layout:

```text
┌────────────────────────────────────────────────────────────┐
│ Task / Stage / Step                       Progress         │
├──────────────┬─────────────────────────────────────────────┤
│              │                                             │
│ Stage        │           Learning Content                  │
│ Navigator    │                                             │
│              │           Interactive Exercise              │
│              │                                             │
│              │           Feedback                          │
│              │                                             │
└──────────────┴─────────────────────────────────────────────┘
```

You may improve this layout if a better UX exists.

---

## 8. Stage and Step Navigation

Users must understand their position in the curriculum without feeling overwhelmed.

Represent:

* Completed stages
* Current stage
* Upcoming stages
* Completed steps
* Current step
* Locked steps when necessary

Possible UI patterns include:

* Vertical learning path
* Compact timeline
* Stepper
* Stage sidebar

Suggested state language:

```text
✓ Completed
● Current
○ Upcoming
```

Avoid overly cartoonish game maps unless the overall design genuinely supports them.

---

## 9. Educational Content

Educational content should feel more polished than a rendered Markdown document.

Create dedicated presentation styles for the following.

### Concept Explanation

Readable body text with strong typography and controlled width.

### Key Idea

Use a visually distinct but subtle callout.

Example:

> **Key idea**
> A model learns patterns from examples rather than relying on explicitly programmed rules.

### Example

Use a slightly differentiated surface.

### Formula

Math should have generous spacing and excellent typography.

### Code

Use high-quality code blocks with:

* Syntax highlighting
* Language label
* Copy action where useful
* Appropriate monospace font

### Hint

Use understated semantic styling.

### Important Concept

Make important concepts obvious without using aggressive warning boxes.

---

## 10. Interactive Questions

Questions should feel like first-class product components.

Support question types such as:

### Multiple Choice

Use large, accessible click targets.

Selected answers should be visually obvious.

### Short Answer

Use high-quality input styling.

### Code or Structured Input

Use dedicated input interfaces where appropriate.

### Classification / Matching

Use cards, chips, drag-and-drop, or selection controls only when they improve usability.

Every question component should support:

* Question
* Optional context
* Answer controls
* Submit / Check Answer action
* Feedback
* Retry
* Alternative question

---

## 11. Feedback UX

Feedback is critical to LEAP.

### Correct Answer

When the learner answers correctly:

* Clearly communicate success
* Use a restrained success state or animation
* Explain why the answer is correct when educationally valuable
* Reveal the next action

Example:

```text
✓ Correct

A decision tree recursively divides the feature space using
conditions that maximize information gain.

[Continue →]
```

Avoid giant celebration animations after every answer.

### Incorrect Answer

Never make the learner feel punished.

Show:

* Clear incorrect state
* Short explanation
* Hint when appropriate
* Retry action
* "Try another question" action

Example:

```text
Not quite.

Remember that supervised learning requires labeled examples
during training.

[Try Again]

[Try a Similar Question]
```

Retrying should feel natural and low-friction.

---

## 12. Locked Progression

If users cannot continue without completing the current requirement, explain why.

Do not simply disable the Next button.

Example:

```text
🔒 Complete this exercise to continue

The next step unlocks after you demonstrate understanding
of this concept.
```

---

## 13. Progress Visualization

Create a sophisticated progress hierarchy.

Example:

```text
Task
├── Stage
│   ├── Step
│   ├── Step
│   └── Step
└── Stage
```

Show progress at multiple levels without creating clutter.

Example:

```text
Sentiment Analysis
72% complete

Stage 4 of 6
Model Evaluation

Step 2 of 6
```

Use subtle progress bars, segmented bars, timelines, or circular indicators only where appropriate.

---

## 14. Task Overview Page

Before a learner begins a task, provide a polished overview.

Include:

* Task title
* Description
* What the learner will build
* Concepts covered
* Estimated scope
* Number of stages
* Current progress
* Learning objectives

Example:

```text
# Sentiment Analysis

Learn how machines classify text based on expressed opinion
and build your understanding from data representation through
model evaluation.
```

### You Will Learn

* Data preprocessing
* Feature extraction
* Supervised learning
* Classification
* Neural networks
* Evaluation

Then display the learning roadmap.

---

## 15. Curriculum / Roadmap

Create a visually satisfying roadmap.

Example:

```text
01  Understanding the Problem          ✓
02  Working with Text Data             ✓
03  Feature Representation             ●
04  Building the Model                 ○
05  Evaluating Performance             ○
06  Improving the System               ○
```

Each stage can expand into its individual steps.

The roadmap should communicate progress immediately.

---

## 16. Completion Experience

When a learner completes a task, create a polished completion experience.

Show:

* Task completed
* Concepts mastered
* Performance summary
* Learning journey
* Areas worth revisiting
* Recommended next task

Avoid excessive gamification.

A subtle celebration animation is acceptable.

---

## 17. Profile and Learning Analytics

Create a useful learner profile rather than a generic account dashboard.

Possible sections:

* Completed tasks
* Concepts mastered
* Accuracy
* Recent activity
* Strengths
* Concepts needing review
* Learning history

Use charts only when they genuinely improve understanding.

---

## 18. AI Learning Features

LEAP may contain or later add AI-assisted learning functionality.

The design system should support features such as:

* Ask LEAP
* Explain this differently
* Give me another example
* Give me a hint
* Generate another question
* Explain my mistake
* Personalized recommendations

Do not make AI assistance look like a floating ChatGPT clone.

Integrate it directly into the learning experience.

For example:

```text
Need help?

[Give me a hint]
[Explain differently]
[Show an example]
```

---

## 19. Microinteractions

Use subtle interactions to make the platform feel premium.

Examples:

* 150–250ms hover transitions
* Button press states
* Progress animation
* Accordion transitions
* Answer-selection states
* Success check animations
* Smooth navigation transitions
* Skeleton loading states

Avoid excessive motion.

Respect:

```css
@media (prefers-reduced-motion: reduce) {
  /* Reduce unnecessary animation */
}
```

---

## 20. Loading, Empty, and Error States

Production software must handle all states.

### Loading

Prefer skeleton loaders over arbitrary spinners where appropriate.

### No Progress Yet

Encourage the learner to begin a task.

### Network Error

Provide:

* Clear explanation
* Retry action

### Failed Content Load

Provide a graceful fallback.

### Completed Task

Clearly differentiate completed content from unavailable content.

---

## 21. Accessibility

Follow WCAG best practices.

Ensure:

* Accessible contrast
* Keyboard navigation
* Visible focus states
* Semantic HTML
* ARIA labels where needed
* Sufficient click/tap targets
* Screen-reader compatibility
* Proper form labels
* Status indicators that do not rely on color alone

---

## 22. Responsive Design

Create breakpoints intentionally.

### Desktop

Use the full learning workspace.

### Tablet

Collapse secondary navigation when necessary.

### Mobile

Make learning content the primary focus.

Do not simply shrink the desktop interface.

For mobile:

* Sidebar becomes a drawer
* Navigation becomes compact
* Cards use available width
* Stage navigator may become a dropdown or bottom sheet
* Sticky bottom Continue action may be used

---

## 23. Technical Expectations

Assume the project uses or can use:

* React
* Next.js
* TypeScript
* Tailwind CSS
* shadcn/ui
* Lucide Icons
* Framer Motion where useful

If the existing project uses a different stack, follow the existing architecture instead.

Build reusable components rather than duplicating page-specific markup.

Suggested components:

```text
AppShell
Sidebar
TopBar
LearningHeader
TaskCard
StageNavigator
StepIndicator
ProgressBar
LearningContent
ConceptBlock
ExampleBlock
FormulaBlock
CodeBlock
QuestionCard
ChoiceOption
FeedbackPanel
HintPanel
AIHelpActions
CompletionCard
MetricCard
ActivityItem
EmptyState
Skeleton
```

---

## 24. Design System

Create reusable design tokens.

Define:

```text
colors
spacing
border radius
shadows
font sizes
line heights
container widths
animation timing
```

Avoid arbitrary styling differences between pages.

Use a consistent spacing scale such as:

```text
4
8
12
16
24
32
48
64
```

---

## 25. UI Density

The product should feel **information-rich but calm**.

Avoid:

* Giant dashboard cards
* Excessive whitespace that causes unnecessary scrolling
* Dense enterprise tables
* Giant hero text inside the application
* Huge buttons everywhere

Use space intentionally.

---

## 26. Iconography

Use a single icon family such as **Lucide**.

Icons should improve comprehension.

Do not add icons simply because empty space exists.

Avoid excessive emoji.

---

## 27. Navigation Behavior

The application should remember the learner's context.

When the user returns to LEAP, prioritize:

> **Continue where you left off**

Navigation between steps should feel nearly instantaneous.

Important actions can remain sticky when useful.

---

## 28. Production-Grade UX Details

Pay special attention to:

* Hover states
* Active states
* Keyboard focus
* Scroll behavior
* Text truncation
* Disabled-state explanations
* Responsive typography
* Sticky headers
* Progress persistence
* Optimistic UI where appropriate
* Loading skeletons
* Smooth content transitions
* Tooltips
* Mobile ergonomics
* Error recovery
* Empty states

These details often separate a student project from professional software.

---

## 29. Avoid Common AI-Generated UI Problems

Do **not** create:

* Excessive gradients
* Every section inside a card
* Random glassmorphism
* Giant rounded containers everywhere
* Glowing buttons
* Gradient text everywhere
* Oversized hero sections inside the app
* Too many pills
* Too many colored badges
* Meaningless charts
* Generic SaaS statistics
* Excessive animation
* Emojis as primary icons
* Inconsistent border radius
* Inconsistent spacing
* Lorem ipsum
* Meaningless sample metrics
* Unnecessary complexity
* A UI that looks like a dashboard template

The product should feel intentionally designed specifically for **learning**.

---

## 30. LEAP Personality

LEAP should communicate:

* **Curiosity**
* **Progress**
* **Mastery**
* **Intelligence**
* **Exploration**

It should feel encouraging but mature.

Think:

> **A personal laboratory for learning machine intelligence.**

Not:

> **A traditional school LMS.**

---

## 31. Branding

Create a subtle visual identity around the concept:

> **LEAP = progression and intellectual growth**

Potential motifs include:

* Steps
* Trajectories
* Connected concepts
* Nodes
* Learning paths
* Progressive motion

Use these motifs subtly.

Do not plaster literal footprints, arrows, or jumping illustrations across the interface.

---

## 32. Product Quality Bar

Before considering any screen complete, evaluate it against the following criteria.

### Visual Quality

* Does this look like professional production software?
* Is typography excellent?
* Is spacing consistent?
* Is visual hierarchy clear?
* Has unnecessary decoration been removed?

### UX Quality

* Can I immediately understand what to do?
* Can I immediately see my progress?
* Is the primary action obvious?
* Are errors recoverable?
* Are locked actions explained?

### Learning Quality

* Is educational content easy to consume?
* Does the UI encourage active learning?
* Does feedback actually help the learner?
* Does progression feel motivating?

### Engineering Quality

* Are components reusable?
* Is responsive behavior intentional?
* Are all major states handled?
* Is accessibility considered?
* Is styling consistent?

---

## 33. Implementation Strategy

Do **not** randomly redesign individual pages.

Follow this process:

1. Inspect the existing LEAP application.
2. Understand its routes and complete user flow.
3. Identify reusable interface patterns.
4. Define the design system.
5. Build or improve shared components.
6. Redesign the global application shell.
7. Redesign the dashboard.
8. Spend significant effort on the core learning experience.
9. Update task, stage, progress, and completion pages.
10. Add intentional responsive behavior.
11. Add loading, error, empty, and locked states.
12. Perform a final consistency and accessibility pass.

Preserve existing business logic unless modification is required for the UI.

Do not break:

* Authentication
* Routing
* Progress persistence
* Task logic
* Question validation
* API integrations
* Database integrations

---

## 34. Implementation Instruction

Do not merely describe what the improved interface could look like.

**Actually implement the redesign.**

When making design decisions, use your judgment as a senior product designer instead of asking about minor stylistic decisions.

If an existing component is visually weak, improve it.

If the information architecture can be improved without breaking functionality, improve it.

If a workflow can be simplified, simplify it.

Prioritize overall product coherence rather than preserving poor existing design decisions.

---

## 35. Final Standard

The finished LEAP interface should look credible enough that screenshots could appear on:

* A startup launch website
* Product Hunt
* A research demonstration
* A university presentation
* A VC pitch deck
* A production EdTech platform

A reviewer should **not** immediately be able to tell that the interface was AI-generated.

The result should feel:

* Intentional
* Cohesive
* Distinctive
* Modern
* Mature
* Production-ready

Above all, make the **learning experience itself** the strongest and most distinctive part of LEAP.
