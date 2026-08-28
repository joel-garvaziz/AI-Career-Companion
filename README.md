# 🎯 AI Career Companion Agent for Internship Matching and Interview Preparation

An AI-powered career assistance platform designed to help students with resume preparation, job matching, skill-gap analysis, cover-letter generation, interview preparation, and career guidance through a set of independent AI agents.

### 📐 Architecture Diagram

`docs/System Architecture.png`

### 🛠️ Tech Stack

`docs/Tech Stack.png`

---

## 🏗️ System Architecture

The system follows a modular, agent-based architecture in which each AI agent operates independently and is responsible for a specific career-related task. A centralized **Agent Gateway** receives requests from the web/chat interface and routes them to the appropriate agent.

### 🤖 The Six Core Agents

* 📄 **Resume Agent** – Assists with resume analysis, extraction, improvement, and generation.

* 🎯 **Job-Resume Matching Agent** – Compares candidate profiles with job requirements and provides matching insights.

* 📊 **Skill Gap Agent** – Identifies missing or weak skills based on target job requirements.

* ✉️ **Cover Letter Agent** – Generates personalized cover letters based on the candidate and job information.

* 🎤 **Interview Agent** – Supports interview preparation through questions, practice, and feedback.

* 🧭 **Career Assistant Agent** – Provides personalized career guidance, recommendations, and assistance.

The agents are designed to remain **autonomous and independent from one another**, allowing each module to be developed, tested, and improved separately.

---

## 📌 Project Status

🚧 **The project is currently under development** as part of an internship project. Individual components are being developed and integrated incrementally.
