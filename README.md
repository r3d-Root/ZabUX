# ZabUX

**ZabUX** is a modern frontend interface for infrastructure monitoring and inventory management. It aims to combine the power of **Zabbix** with tools like **NetBox**, creating a unified and user-friendly platform for network and systems operations teams.

---

## 🚀 Project Vision

ZabUX is designed to:

- Replace or supplement the native Zabbix frontend with a more intuitive, responsive UI.
- Integrate Zabbix alerting, metrics, and host data with inventory and topology from tools like NetBox.
- Allow for future integrations with other network tools (e.g., NMS, asset trackers, IPAM).

---

## 🔧 Tech Stack

- **Backend:** Python Flask (Blueprints + RESTful API)
- **Frontend:** HTML + Bootstrap (initially), with future enhancements in JS frameworks or REST UI
- **Integrations:** Zabbix API, NetBox API (planned)

---

## 🗂️ Project Structure

```bash
ZabUX/
│
├── app/
│   ├── api/            # API routes
│   ├── main/           # Frontend views
│   ├── templates/      # Jinja HTML templates
│   └── __init__.py     # App factory
│
├── run.py              # Entry point
├── .env                # Environment config (not committed)
├── .gitignore
├── requirements.txt
└── README.md
