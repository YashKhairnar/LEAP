# LEAP: conceptual-bridge tutor

LEAP teaches three machine-learning tasks through optional Java connections or everyday
examples: sentiment classification, image classification, and regression. The web application collects question responses and
code exploration; the research project develops a learner-state world model from histories.

## Start here

- [Run locally](docs/local-development.md)
- [Find the right file](docs/project-structure.md)
- [Current implementation and remaining work](docs/status.md)
- [Collection protocol and exports](docs/collection.md)
- [Deploy the services](docs/deployment.md)
- [Research documentation](LEAP/docs/README.md)

## Repository map

```text
WebApp/
├── frontend/        Next.js learner interface
├── backend/         FastAPI, persistence, tutoring, scoring, code execution
├── model_service/   Private world-model inference service
├── LEAP/            Research models, preprocessing, training and experiments
├── docs/            Cross-project setup, architecture, collection and deployment
└── render.yaml      Backend and model-service deployment configuration
```

The service folders and existing URLs are intentionally stable. Within the app, code is
grouped by feature; within `LEAP`, code remains grouped by research component. Dataset files,
participant databases and promoted weights have not been relocated.

## Current boundary

The app has six stages per task, fixed executable Python examples and authored experiments,
generated explanations/questions, and ten final MCQs per task. During collection, teaching
actions are sampled uniformly; the world model records an experimental shadow recommendation.
An inference-service outage does not stop that random assignment.

This is a technical-pilot implementation, not a validated adaptive teaching policy. Formal
collection still requires approved consent and a reviewed learning-gain assessment protocol.
No reorganization or export automatically trains or promotes a checkpoint.
