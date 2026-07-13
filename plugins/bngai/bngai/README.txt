# 🛰️ BNG AI QGIS Plugin

## 📘 Overview
The **BNG AI QGIS Plugin** is a custom geospatial extension built for internal use at **AiDash**, designed to enhance spatial data visualization, AI-assisted analytics, and field mapping workflows within **QGIS Desktop**.

It integrates with AiDash’s backend APIs and provides tools for map interaction, feature editing, and data synchronization between local QGIS environments and remote services.

---

What's Next:

  * Copy the entire directory containing your new plugin to the QGIS plugin
    directory

  * Compile the resources file using pyrcc5

  * Run the tests (``make test``)

  * Test the plugin by enabling it in the QGIS plugin manager

  * Customize it by editing the implementation file: ``bngai.py``

  * Create your own custom icon, replacing the default icon.png

  * Modify your user interface by opening bngaiPOC_dialog_base.ui in Qt Designer

  * You can use the Makefile to compile your Ui and resource files when
    you make changes. This requires GNU make (gmake)

For more information, see the PyQGIS Developer Cookbook at:
http://www.qgis.org/pyqgis-cookbook/index.html

(C) 2011-2018 GeoApt LLC - geoapt.com

---

## 🧩 Roles & SPOs (Single Points of Ownership)

| Area | Owner | Responsibility |
|------|--------|----------------|
| **Plugin Architecture** | [Frontend Engg – SDE-3 (Vivek)] | Codebase ownership, build & deployment automation |
| **API / Backend Integration** | Backend SPO | Maintain endpoints, schema compatibility |
| **QA & Validation** | QA SPO | Plugin functional and regression testing |
| **Release Management** | DevOps / SDE-3 | Version tagging, Bitbucket CI/CD, release uploads |
| **Documentation & Metadata** | PM / Technical Writer | Maintain metadata.txt, changelogs, and README updates |

---

## ⚙️ Environment Setup

### 🔹 1. Development Environment

#### **System Requirements**
- QGIS ≥ 3.22
- Python ≥ 3.9
- `PyQt5`, `qgis.core`, and `qgis.gui` modules available (via QGIS install)

#### **Steps**
1. **Clone the repository**
   ```bash
   git clone git@bitbucket.org:aidash/bngai-qgis-plugin.git
   cd bngai-qgis-plugin

2.	Create a symlink to QGIS plugin directory
ln -s $(pwd) ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/bngai-qgis-plugin

3.	Reload plugin in QGIS
	•	Open QGIS → Plugins → Manage and Install Plugins → Installed
	•	Check/uncheck the plugin to reload changes.
	4.	For UI changes (Qt Designer)

4.	For UI changes (Qt Designer)
pyuic5 ui_main_dialog.ui -o ui_main_dialog.py
pyrcc5 resources.qrc -o resources_rc.py

 2. QA / Testing Environment

Checkout release candidate branch
Build plugin zip
  make package
  # or using pb_tool
  pb_tool package
Distribute zip to QA testers

rm -rf bngai_*
zip -r bngai_qa.zip bngai -x "__MACOSX/*" "*/.DS_Store"
zip -r bngai_uat.zip bngai -x "__MACOSX/*" "*/.DS_Store"
zip -r bngai_prod.zip bngai -x "__MACOSX/*" "*/.DS_Store"


