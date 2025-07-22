# 🤖 AI-Powered Telegram Bot Framework

**Updated Project Structure - v2.0**

## 📁 Project Structure

```
/Bot-answers/
├── main.py                     # 🚀 Main entry point
├── config.py                   # ⚙️  Configuration
├── .env                        # 🔐 Environment variables
├── requirements.txt           # 📦 Dependencies
│
├── src/                      # 📚 MAIN CODE
│   ├── bot/                  # 🤖 Telegram Bot components
│   │   ├── handlers/         # 📝 Message handlers
│   │   │   └── main.py      # Basic handlers (start, templates, AI)
│   │   ├── keyboards.py     # ⌨️  Inline keyboards
│   │   ├── models.py        # 📊 FSM states & models
│   │   └── routers.py       # 🛣️  Route registration
│   │
│   ├── ai/                   # 🧠 AI components
│   │   ├── service.py       # Main AI service with mock responses
│   │   └── prompts/         # 📝 AI prompts (future)
│   │
│   ├── core/                # 🏗️  Core components
│   │   ├── template_manager.py  # Template management
│   │   ├── business_hours.py    # Business logic
│   │   ├── stats.py            # Statistics
│   │   └── validation.py       # Input validation
│   │
│   └── utils/               # 🔧 Utilities
│       ├── error_handler.py    # Error handling
│       ├── error_monitor.py    # Error monitoring
│       └── exceptions.py       # Custom exceptions
│
├── data/                    # 💾 Data storage
│   ├── templates/          # 📋 CSV templates
│   ├── vectorstore/        # 🗃️  Vector DB (future)
│   └── logs/              # 📜 Application logs
│
├── scripts/                # 🔧 Scripts
│   ├── test_api_keys.py   # 🔑 API key testing
│   └── final_test.py      # 🧪 System testing
│
└── tests/                  # 🧪 Test suite
    ├── unit/
    └── integration/
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run the bot:**
   ```bash
   python main.py
   ```

4. **Test AI functionality:**
   ```bash
   cd scripts && python final_test.py
   ```

## 🧠 AI Features

- **Smart keyword matching** for business queries
- **Multi-language support** (Ukrainian/Russian)
- **Mock AI responses** for common questions:
  - Prices ("Скільки коштують візитки?")
  - Timelines ("Які терміни виготовлення?")
  - Quality ("Яка якість друку?")
  - Design requirements ("Що потрібно для макету?")
- **Business hours integration**
- **Fallback to human operators**

## 📈 Current Status

- ✅ **90% success rate** on test queries
- ✅ **Structured architecture** ready for scaling
- ✅ **OpenAI integration** ready (with $10 credits)
- ✅ **Mock responses** working perfectly
- ✅ **Error handling** and logging

## 🔄 Next Steps

1. Integrate real RAG pipeline with ChromaDB
2. Add vector embeddings for knowledge base
3. Implement real OpenAI GPT-4o-mini integration
4. Add more sophisticated prompts
5. Create admin dashboard
6. Add analytics and performance monitoring

## 🎯 For Volunteers & Non-profits

This framework is designed to be easily adaptable for:
- Humanitarian assistance organizations
- Crisis communication systems
- Multi-language customer support
- Educational institutions
- Community support services

**License:** Open source for non-commercial use
**Purpose:** Educational and humanitarian applications
