<h1 align="center">🤖 Multi-Agent Document & PPT Generation Chatbot</h1>

<p align="center">
  An enterprise-grade <b>multi-agent AI chatbot</b> for document analysis,
  enterprise RAG, real-time web research, editable DOCX/PPTX generation,
  conversational editing, document conversion, validation, citations,
  traceability, and version management.
</p>

<p align="center">
  <b>Gemini</b> • <b>FastAPI</b> • <b>Streamlit</b> •
  <b>Pinecone</b> • <b>FastEmbed</b> • <b>Tavily</b> •
  <b>Tesseract OCR</b> • <b>python-docx</b> • <b>python-pptx</b>
</p>

<hr>

<h2>📌 Overview</h2>

<p>
The <b>Multi-Agent Document & PPT Generation Chatbot</b> is an enterprise-grade
Proof of Concept designed to understand natural-language user requests,
analyze uploaded documents and presentation templates, perform real-time web
research, retrieve information from enterprise knowledge sources, and generate
professional editable documents and presentations.
</p>

<p>
The system follows a specialized <b>multi-agent architecture</b> where different
agents are responsible for orchestration, document analysis, PPT analysis,
web research, enterprise RAG, document generation, PPT generation, validation,
and conversational artifact editing.
</p>

<p>
Users can upload existing <b>PDF, DOCX, PPT/PPTX, PNG, JPG, and JPEG</b> files
and interact with the system through natural-language requests.
</p>

<p>
The generated artifacts can subsequently be edited through conversational
commands while maintaining their existing structure and context.
</p>

<hr>

<h2>🎯 Assignment Objective</h2>

<p>
The project was developed to satisfy the requirements of the
<b>Multi-Agent AI Chatbot for Document & PPT Generation</b> assignment.
</p>

<p>The system demonstrates:</p>

<ul>
  <li>🧠 Multi-agent orchestration</li>
  <li>📄 Document analysis</li>
  <li>📊 PPT template analysis</li>
  <li>🌐 Real-time web research</li>
  <li>🧠 Enterprise Retrieval-Augmented Generation (RAG)</li>
  <li>🔎 Pinecone vector database integration</li>
  <li>🖼️ OCR processing for image/scanned content</li>
  <li>📝 Editable DOCX generation</li>
  <li>📊 Editable PPTX generation</li>
  <li>🎨 Template style and structure preservation</li>
  <li>💬 Conversational artifact editing</li>
  <li>🔄 DOCX ↔ PPTX conversion</li>
  <li>📚 Source citations and traceability</li>
  <li>🗂️ Artifact version management</li>
  <li>✅ Generated artifact validation</li>
  <li>🔐 Modular backend APIs</li>
</ul>

<hr>

<h2>✨ Key Features</h2>

<h3>🧩 1. Multi-Agent Architecture</h3>

<p>
The application uses specialized agents instead of implementing the entire
workflow inside a single LLM call.
</p>

<ul>
  <li>🎯 Supervisor / Orchestrator Agent</li>
  <li>📄 Document Analyzer Agent</li>
  <li>📊 PPT Analyzer Agent</li>
  <li>🌐 Web Research Agent</li>
  <li>🧠 RAG Agent</li>
  <li>📝 Document Generation Agent</li>
  <li>📊 PPT Generation Agent</li>
  <li>✅ Validation Agent</li>
  <li>✏️ Conversational Editing Agent</li>
</ul>

<p>
The Supervisor determines which agents are required for each user request and
coordinates the execution pipeline.
</p>

<hr>

<h3>📄 2. Document Analysis</h3>

<p>
The system can analyze uploaded documents and extract useful structural and
content information including:
</p>

<ul>
  <li>Document type</li>
  <li>Tone</li>
  <li>Heading hierarchy</li>
  <li>Fonts</li>
  <li>Primary font</li>
  <li>Paragraph information</li>
  <li>Tables</li>
  <li>Section titles</li>
  <li>Title information</li>
  <li>Content structure</li>
</ul>

<p>
Supported document inputs include:
</p>

<ul>
  <li>PDF</li>
  <li>DOCX</li>
  <li>Scanned documents</li>
  <li>Images</li>
</ul>

<hr>

<h3>📊 3. PPT Template Analysis</h3>

<p>
Existing PowerPoint templates can be uploaded and analyzed to understand
presentation-level formatting and design characteristics.
</p>

<p>The system considers:</p>

<ul>
  <li>Slide dimensions</li>
  <li>Visual style</li>
  <li>Primary fonts</li>
  <li>Layout information</li>
  <li>Slide structure</li>
  <li>Content patterns</li>
  <li>Presentation formatting</li>
</ul>

<p>
Generated presentations use the analyzed template information to maintain the
overall visual style and structure.
</p>

<hr>

<h3>🌐 4. Real-Time Web Research</h3>

<p>
The Web Research Agent uses <b>Tavily</b> to perform real-time web research
when the user's request requires current or recent information.
</p>

<p>Example request:</p>

<pre>
Research the latest developments in Generative AI and
create a concise report with sources.
</pre>

<p>The research workflow is:</p>

<pre>
User Query
    ↓
Supervisor
    ↓
Web Research Agent
    ↓
Tavily Search
    ↓
Relevant Web Sources
    ↓
Research Findings
    ↓
Content Planning / Generation
</pre>

<p>
Web research results are incorporated into generated content and associated
with source citations.
</p>

<hr>

<h3>🧠 5. Enterprise RAG</h3>

<p>
The application implements Retrieval-Augmented Generation for retrieving
relevant information from uploaded enterprise documents.
</p>

<p>The RAG pipeline is:</p>

<pre>
Uploaded Document
      ↓
Text Extraction
      ↓
Chunking
      ↓
FastEmbed Embeddings
      ↓
Pinecone Vector Database
      ↓
Semantic Similarity Search
      ↓
Relevant Chunks
      ↓
LLM / Content Generation
</pre>

<p>
<b>FastEmbed</b> is used for local embedding generation and
<b>Pinecone</b> is used as the enterprise vector database.
</p>

<p>
The system also supports a local FAISS vector-store fallback for development
and environments where Pinecone is unavailable.
</p>

<hr>

<h3>🔎 6. Source Citations & Traceability</h3>

<p>
The application maintains source information throughout the pipeline.
Retrieved content can be associated with citation identifiers such as:
</p>

<pre>
RAG-001
RAG-002
WEB-001
WEB-002
</pre>

<p>
Each orchestration request generates a trace identifier that allows the
execution flow to be inspected.
</p>

<p>Example:</p>

<pre>
Trace ID: trace_d8cd9d501e
</pre>

<p>
The trace can contain information about:
</p>

<ul>
  <li>User request</li>
  <li>Execution plan</li>
  <li>Agents executed</li>
  <li>Document analysis</li>
  <li>PPT analysis</li>
  <li>Web research</li>
  <li>RAG retrieval</li>
  <li>Citations</li>
  <li>Generated artifact IDs</li>
  <li>Validation results</li>
  <li>Warnings</li>
</ul>

<hr>

<h3>🖼️ 7. OCR / Image Processing</h3>

<p>
The system supports scanned and image-based content through OCR processing.
</p>

<p>
Image formats supported include:
</p>

<ul>
  <li>PNG</li>
  <li>JPG</li>
  <li>JPEG</li>
</ul>

<p>
The OCR pipeline uses <b>Tesseract OCR</b> through the
<b>pytesseract</b> Python library.
</p>

<pre>
Image / Scanned Document
          ↓
      OCR Engine
          ↓
     Extracted Text
          ↓
 Document Analysis
          ↓
      RAG / LLM
          ↓
       Response
</pre>

<p>
The system also supports OCR fallback for scanned PDFs when selectable text
cannot be extracted.
</p>

<hr>

<h3>📝 8. Editable DOCX Generation</h3>

<p>
The Document Generation Agent generates real editable Microsoft Word
documents using <b>python-docx</b>.
</p>

<p>Generated reports can contain:</p>

<ul>
  <li>Title</li>
  <li>Executive Summary</li>
  <li>Main Sections</li>
  <li>Key Findings</li>
  <li>Important Details</li>
  <li>Conclusion</li>
  <li>Sources / Citations</li>
</ul>

<p>
The generated output is an actual editable <b>.docx</b> file rather than a
PDF or image representation.
</p>

<hr>

<h3>📊 9. Editable PPTX Generation</h3>

<p>
The PPT Generation Agent creates editable PowerPoint presentations using
<b>python-pptx</b>.
</p>

<p>
The content is adapted to presentation format instead of simply copying
large document paragraphs onto slides.
</p>

<p>Generated presentations can contain:</p>

<ul>
  <li>Title slide</li>
  <li>Overview</li>
  <li>Main sections</li>
  <li>Key points</li>
  <li>Important details</li>
  <li>Conclusion</li>
  <li>Sources</li>
</ul>

<p>
Dense sections can automatically be divided across multiple slides.
</p>

<hr>

<h3>🎨 10. Template-Based Generation</h3>

<p>
The system supports generation using uploaded templates.
</p>

<p>
For example:
</p>

<pre>
Uploaded PDF
     +
Uploaded DOCX Template
     ↓
Document Analysis
     ↓
Content Planning
     ↓
Generated Editable DOCX
</pre>

<p>Similarly:</p>

<pre>
Uploaded PDF
     +
Uploaded PPTX Template
     ↓
PPT Analysis
     ↓
Content Planning
     ↓
Generated Editable PPTX
</pre>

<p>
The system attempts to preserve the template's overall:
</p>

<ul>
  <li>Structure</li>
  <li>Tone</li>
  <li>Formatting</li>
  <li>Visual style</li>
  <li>Content organization</li>
</ul>

<hr>

<h3>💬 11. Conversational Artifact Editing</h3>

<p>
Generated artifacts can be modified through natural-language instructions.
</p>

<p>Examples:</p>

<pre>
Add an executive summary.
</pre>

<pre>
Make the presentation more concise.
</pre>

<pre>
Add a competitive analysis section.
</pre>

<pre>
Update the report using the latest web information.
</pre>

<p>
The Conversational Editing Agent loads the existing content plan, applies the
requested modification, generates a new version, and preserves the artifact's
existing context.
</p>

<hr>

<h3>🗂️ 12. Version Management</h3>

<p>
Generated artifacts maintain version history.
</p>

<p>Example:</p>

<pre>
Document
 ├── v1
 └── v2
</pre>

<p>
Each version maintains associated content-plan information and metadata.
</p>

<p>
This allows users to track changes made through conversational editing.
</p>

<hr>

<h3>🔄 13. Document / Presentation Conversion</h3>

<p>
The application supports conversion between document and presentation formats.
</p>

<pre>
DOCX → PPTX
</pre>

<pre>
PPTX → DOCX
</pre>

<p>
The conversion pipeline adapts the content to the target format instead of
simply renaming or copying the source file.
</p>

<hr>

<h3>✅ 14. Artifact Validation</h3>

<p>
Generated artifacts are validated before being presented as successful
outputs.
</p>

<h4>DOCX Validation</h4>

<ul>
  <li>File can be opened</li>
  <li>Expected structure exists</li>
  <li>Document contains body content</li>
  <li>Required sections can be checked</li>
  <li>Citations are validated</li>
</ul>

<h4>PPTX Validation</h4>

<ul>
  <li>File can be opened</li>
  <li>Slides are structurally valid</li>
  <li>Slides are not empty</li>
  <li>Requested slide count can be validated when applicable</li>
  <li>Citations are validated</li>
</ul>

<p>
Validation status is displayed in the Streamlit artifact panel.
</p>

<hr>

<h2>🏗️ System Architecture</h2>

<pre>
                         ┌─────────────────────┐
                         │      User           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Streamlit Frontend │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   FastAPI Backend   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │ Supervisor / Orchestrator│
                       └────────────┬────────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      Document Agent          PPT Agent             Web Research
             │                      │                      │
             │                      │                   Tavily
             │                      │
             └──────────────┬───────┘
                            │
                            ▼
                       RAG Agent
                            │
                            ▼
                   FastEmbed Embeddings
                            │
                            ▼
                      Pinecone DB
                            │
                            ▼
                    Content Planning
                            │
                  ┌─────────┴─────────┐
                  ▼                   ▼
          DOCX Generator        PPTX Generator
                  │                   │
                  └─────────┬─────────┘
                            ▼
                     Validation Agent
                            │
                            ▼
                      Artifact Store
                            │
                            ▼
                   Version / Edit / Convert
</pre>

<hr>

<h2>🧠 Multi-Agent Workflow</h2>

<ol>

<li>User uploads documents/templates and enters a natural-language request.</li>

<li>The Supervisor Agent analyzes the request and creates an execution plan.</li>

<li>The Document Analyzer processes PDF/DOCX files when required.</li>

<li>The PPT Analyzer processes uploaded PPT/PPTX templates when required.</li>

<li>The Web Research Agent performs real-time research through Tavily when
current information is requested.</li>

<li>The RAG Agent retrieves relevant enterprise knowledge from Pinecone.</li>

<li>The Content Planner combines the request, research findings, retrieved
knowledge, and template information.</li>

<li>The Document Generator creates an editable DOCX when requested.</li>

<li>The PPT Generator creates an editable PPTX when requested.</li>

<li>The Validation Agent verifies the generated artifact.</li>

<li>The Artifact Store saves the generated artifact and its version metadata.</li>

<li>The user can subsequently modify the artifact using natural-language
instructions.</li>

</ol>

<hr>

<h2>🛠️ Technology Stack</h2>

<table>

<tr>
<th>Category</th>
<th>Technology</th>
</tr>

<tr>
<td>Programming Language</td>
<td>Python</td>
</tr>

<tr>
<td>Frontend</td>
<td>Streamlit</td>
</tr>

<tr>
<td>Backend</td>
<td>FastAPI</td>
</tr>

<tr>
<td>ASGI Server</td>
<td>Uvicorn</td>
</tr>

<tr>
<td>LLM</td>
<td>Google Gemini</td>
</tr>

<tr>
<td>Web Research</td>
<td>Tavily</td>
</tr>

<tr>
<td>Embeddings</td>
<td>FastEmbed</td>
</tr>

<tr>
<td>Vector Database</td>
<td>Pinecone</td>
</tr>

<tr>
<td>Local Vector Store / Fallback</td>
<td>FAISS</td>
</tr>

<tr>
<td>PDF Processing</td>
<td>PyMuPDF</td>
</tr>

<tr>
<td>DOCX Processing</td>
<td>python-docx</td>
</tr>

<tr>
<td>PPTX Processing</td>
<td>python-pptx</td>
</tr>

<tr>
<td>OCR</td>
<td>Tesseract + pytesseract</td>
</tr>

<tr>
<td>Image Processing</td>
<td>Pillow</td>
</tr>

<tr>
<td>Configuration</td>
<td>python-dotenv / pydantic-settings</td>
</tr>

<tr>
<td>Testing</td>
<td>pytest</td>
</tr>

</table>

<hr>

<h2>📂 Project Structure</h2>

<pre>
docgen-multiagent_Phase16/
│
├── backend/
│   ├── agents/
│   │   ├── supervisor.py
│   │   ├── document_analyzer.py
│   │   ├── ppt_analyzer.py
│   │   ├── web_research.py
│   │   ├── rag_agent.py
│   │   ├── document_generator.py
│   │   ├── ppt_generator.py
│   │   ├── conversational_editor.py
│   │   └── converter.py
│   │
│   ├── api/
│   │   ├── chat.py
│   │   ├── ingest.py
│   │   ├── generate.py
│   │   ├── convert.py
│   │   └── trace.py
│   │
│   ├── services/
│   │   ├── llm_service.py
│   │   ├── extraction_service.py
│   │   ├── embedding_service.py
│   │   ├── vector_store.py
│   │   ├── ocr_service.py
│   │   ├── artifact_store.py
│   │   └── citation_service.py
│   │
│   ├── schemas/
│   └── main.py
│
├── frontend/
│   └── app.py
│
├── data/
│   ├── samples/
│   │   ├── templates/
│   │   │   └── report_template.docx
│   │   └── outputs/
│   │       ├── sample_report.docx
│   │       └── sample_presentation.pptx
│   │
│   ├── generated/
│   ├── uploads/
│   ├── templates/
│   ├── versions/
│   └── knowledge_base/
│
├── tests/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
</pre>

<hr>

<h2>⚙️ Installation</h2>

<h3>1. Clone the Repository</h3>

<pre>
git clone &lt;YOUR_GITHUB_REPOSITORY_URL&gt;
cd docgen-multiagent_Phase16
</pre>

<h3>2. Create Virtual Environment</h3>

<h4>Windows</h4>

<pre>
python -m venv venv
venv\Scripts\activate
</pre>

<h4>Linux / macOS</h4>

<pre>
python3 -m venv venv
source venv/bin/activate
</pre>

<h3>3. Install Python Dependencies</h3>

<pre>
pip install -r requirements.txt
</pre>

<h3>4. Configure Environment Variables</h3>

<p>
Create a <code>.env</code> file from <code>.env.example</code>.
</p>

<pre>
copy .env.example .env
</pre>

<p>
Configure the required API keys and providers inside <code>.env</code>.
</p>

<hr>

<h2>🔑 Environment Configuration</h2>

<p>Typical configuration:</p>

<pre>
LLM_PROVIDER=gemini
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

VECTOR_STORE=pinecone
PINECONE_API_KEY=YOUR_PINECONE_API_KEY
PINECONE_INDEX_NAME=docgen-multiagent

WEB_SEARCH_PROVIDER=tavily
TAVILY_API_KEY=YOUR_TAVILY_API_KEY
</pre>

<p>
Never commit the <code>.env</code> file or API keys to GitHub.
</p>

<hr>

<h2>🖼️ Tesseract OCR Setup</h2>

<p>
The Python package <code>pytesseract</code> requires the Tesseract OCR engine
to be installed separately.
</p>

<h3>Windows</h3>

<ol>
<li>Install Tesseract OCR.</li>
<li>Add the Tesseract installation directory to PATH.</li>
<li>Restart the terminal.</li>
</ol>

<p>Verify installation:</p>

<pre>
tesseract --version
</pre>

<p>
If required, configure the executable path in the OCR service.
</p>

<hr>

<h2>▶️ Running the Application</h2>

<h3>Start the FastAPI Backend</h3>

<p>Open Terminal 1:</p>

<pre>
venv\Scripts\activate
uvicorn backend.main:app --reload --port 8000
</pre>

<p>
The backend will be available at:
</p>

<pre>
http://127.0.0.1:8000
</pre>

<h3>Start the Streamlit Frontend</h3>

<p>Open Terminal 2:</p>

<pre>
venv\Scripts\activate
streamlit run frontend/app.py
</pre>

<p>
The Streamlit interface will normally be available at:
</p>

<pre>
http://localhost:8501
</pre>

<hr>

<h2>💻 How to Use</h2>

<h3>Step 1 — Upload Files</h3>

<p>
Upload one or more supported files through the Streamlit sidebar.
</p>

<ul>
  <li>PDF</li>
  <li>DOCX</li>
  <li>PPT</li>
  <li>PPTX</li>
  <li>PNG</li>
  <li>JPG</li>
  <li>JPEG</li>
</ul>

<h3>Step 2 — Enter a Request</h3>

<p>Example:</p>

<pre>
Research the latest Generative AI trends and create a
proposal and presentation using the uploaded templates.
</pre>

<h3>Step 3 — Agent Execution</h3>

<p>
The application automatically determines which agents are needed.
</p>

<h3>Step 4 — Review Results</h3>

<p>
The UI displays agent activity, citations, trace information, generated
artifacts, and validation status.
</p>

<h3>Step 5 — Edit the Artifact</h3>

<p>
Select the generated artifact and enter a natural-language modification.
</p>

<p>Example:</p>

<pre>
Add a short Key Takeaways section at the end of the document.
</pre>

<p>
A new artifact version is generated.
</p>

<hr>

<h2>🧪 Example Assignment Workflow</h2>

<p>
The assignment provides the following type of workflow:
</p>

<pre>
User uploads:

Company_Proposal.docx
Company_Template.pptx

User asks:

"Research the latest Generative AI trends and create a
proposal and 12-slide presentation using the same tone
and style as the uploaded files."
</pre>

<p>The system performs:</p>

<ol>
  <li>Analyze uploaded templates</li>
  <li>Perform real-time web research</li>
  <li>Retrieve enterprise knowledge using RAG</li>
  <li>Generate document and presentation</li>
  <li>Validate generated content</li>
  <li>Provide citations and sources</li>
  <li>Return editable DOCX and PPTX files</li>
</ol>

<p>
The user can then continue with requests such as:
</p>

<ul>
  <li>Add an executive summary.</li>
  <li>Make the presentation more concise.</li>
  <li>Add a competitive analysis section.</li>
  <li>Update the report using the latest web information.</li>
</ul>

<hr>

<h2>🔄 Artifact Editing Workflow</h2>

<pre>
Generated Artifact
       ↓
User Edit Request
       ↓
Conversational Editing Agent
       ↓
Load Existing Content Plan
       ↓
Apply Requested Changes
       ↓
Generate New Version
       ↓
Validate
       ↓
Save Version
</pre>

<p>Example:</p>

<pre>
v1
 ↓
"Add Key Takeaways"
 ↓
v2
</pre>

<hr>

<h2>🔄 DOCX ↔ PPTX Conversion</h2>

<p>
The application provides document/presentation conversion capabilities.
</p>

<pre>
DOCX → PPTX
</pre>

<pre>
PPTX → DOCX
</pre>

<p>
The conversion process adapts content to the target format and stores the
result as a separate artifact.
</p>

<hr>

<h2>📡 Backend API</h2>

<table>

<tr>
<th>Endpoint</th>
<th>Purpose</th>
</tr>

<tr>
<td>GET /health</td>
<td>Check backend health and configured providers</td>
</tr>

<tr>
<td>POST /upload</td>
<td>Upload supported files</td>
</tr>

<tr>
<td>POST /ingest/{file_id}</td>
<td>Extract and normalize uploaded file content</td>
</tr>

<tr>
<td>POST /chat</td>
<td>Run the multi-agent orchestration pipeline</td>
</tr>

<tr>
<td>POST /generate/document</td>
<td>Generate an editable DOCX</td>
</tr>

<tr>
<td>POST /generate/presentation</td>
<td>Generate an editable PPTX</td>
</tr>

<tr>
<td>GET /trace/{trace_id}</td>
<td>Retrieve orchestration trace information</td>
</tr>

<tr>
<td>POST /validate/{artifact_id}</td>
<td>Validate a generated artifact</td>
</tr>

</table>

<hr>

<h2>🧪 Testing</h2>

<p>
The project includes automated tests using <b>pytest</b>.
</p>

<pre>
pytest -v
</pre>

<p>
Individual test modules can also be executed independently.
</p>

<pre>
pytest tests/test_rag.py -v
</pre>

<pre>
pytest tests/test_web_research.py -v
</pre>

<pre>
pytest tests/test_document_generation.py -v
</pre>

<pre>
pytest tests/test_ppt_generation.py -v
</pre>

<pre>
pytest tests/test_validation.py -v
</pre>

<hr>

<h2>📦 Sample Templates & Generated Outputs</h2>

<p>
Sample assignment artifacts are included in:
</p>

<pre>
data/
└── samples/
    ├── templates/
    │   └── report_template.docx
    │
    └── outputs/
        ├── sample_report.docx
        └── sample_presentation.pptx
</pre>

<p>
These files demonstrate template-based generation and editable output
generation.
</p>

<hr>

<h2>📋 Assignment Requirement Coverage</h2>

<table>

<tr>
<th>Assignment Requirement</th>
<th>Status</th>
</tr>

<tr>
<td>Multi-agent chatbot with Supervisor/Orchestrator</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Document and PPT template analysis</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Real-time web search and research</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Enterprise RAG with vector database</td>
<td>✅ Pinecone</td>
</tr>

<tr>
<td>PDF support</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>DOCX support</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>PPT/PPTX support</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Image/scanned document support</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>OCR/vision processing</td>
<td>✅ Tesseract OCR</td>
</tr>

<tr>
<td>Editable DOCX generation</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Editable PPTX generation</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Template tone and structure preservation</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Template formatting / visual style</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Conversational editing</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>DOCX ↔ PPTX conversion</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Source citations and traceability</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Version management</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Secure/modular backend APIs</td>
<td>✅ Implemented</td>
</tr>

<tr>
<td>Sample templates and outputs</td>
<td>✅ Included</td>
</tr>

<tr>
<td>Complete documentation</td>
<td>📚 README / Documentation</td>
</tr>

<tr>
<td>requirements.txt</td>
<td>✅ Included</td>
</tr>

</table>

<hr>

<h2>⚠️ Configuration & Limitations</h2>

<ul>

<li>
API keys for Gemini, Pinecone, and Tavily must be configured in
<code>.env</code>.
</li>

<li>
Tesseract OCR requires the system-level Tesseract executable in addition
to the Python <code>pytesseract</code> package.
</li>

<li>
The first FastEmbed model initialization may require downloading the
embedding model.
</li>

<li>
Real-time web research requires a valid Tavily API key.
</li>

<li>
Pinecone functionality requires a valid Pinecone API key and configured
index.
</li>

</ul>

<hr>

<h2>🔐 Security</h2>

<ul>
  <li>API keys are loaded through environment variables.</li>
  <li><code>.env</code> is excluded from Git.</li>
  <li>Uploaded/generated runtime data is excluded from Git.</li>
  <li>Backend functionality is separated into modular APIs and services.</li>
  <li>Generated artifacts are validated before being reported as successful.</li>
</ul>

<hr>

<h2>🚀 Deployment</h2>

<p>
The project is designed to be deployed through GitHub for demonstration and
evaluation purposes.
</p>

<p>
The repository should contain:
</p>

<ul>
  <li>Complete source code</li>
  <li>requirements.txt</li>
  <li>.env.example</li>
  <li>README.md</li>
  <li>Sample templates</li>
  <li>Sample generated outputs</li>
  <li>Automated tests</li>
</ul>

<p>
Sensitive credentials must never be committed to the repository.
</p>

<hr>

<h2>🎥 Demonstration Workflow</h2>

<p>
A recommended demonstration sequence is:
</p>

<ol>
  <li>Start FastAPI backend.</li>
  <li>Start Streamlit frontend.</li>
  <li>Upload a PDF/document.</li>
  <li>Upload a DOCX template.</li>
  <li>Upload a PPTX template.</li>
  <li>Ask for research + proposal + presentation.</li>
  <li>Show document analysis.</li>
  <li>Show PPT template analysis.</li>
  <li>Show Tavily research.</li>
  <li>Show Pinecone RAG retrieval.</li>
  <li>Show generated DOCX.</li>
  <li>Show generated PPTX.</li>
  <li>Show validation status.</li>
  <li>Edit the generated document.</li>
  <li>Show v1 → v2 version history.</li>
  <li>Convert DOCX ↔ PPTX.</li>
  <li>Show traceability information.</li>
</ol>

<hr>

<h2>🤝 Future Improvements</h2>

<ul>
  <li>Production-grade authentication and authorization</li>
  <li>Persistent conversation management</li>
  <li>Advanced template style cloning</li>
  <li>More sophisticated layout intelligence</li>
  <li>Distributed task execution</li>
  <li>Cloud deployment and monitoring</li>
  <li>Advanced observability dashboards</li>
</ul>

<hr>

<h2>👨‍💻 Author</h2>

<p>
<b>Vedant Gaikwad</b>
</p>

<p>
Electronics & Telecommunication Engineering
</p>

<p>
AI / Machine Learning / Generative AI
</p>

<hr>

<h2>📄 Assignment Deliverables</h2>

<p>
The project is organized to provide the deliverables requested in the
assignment:
</p>

<ul>
  <li>✅ Fully functional multi-agent chatbot POC</li>
  <li>✅ Complete source code</li>
  <li>✅ Document/PPT template analysis</li>
  <li>✅ Web research</li>
  <li>✅ Enterprise RAG</li>
  <li>✅ Editable DOCX generation</li>
  <li>✅ Editable PPTX generation</li>
  <li>✅ Conversational artifact editing</li>
  <li>✅ Source/citation traceability</li>
  <li>✅ Sample templates</li>
  <li>✅ Sample generated outputs</li>
  <li>✅ Project documentation</li>
  <li>✅ README setup instructions</li>
  <li>✅ Usage guidelines</li>
  <li>✅ requirements.txt</li>
</ul>

<p>
The assignment also recommends GitHub deployment and a working project
demonstration video.
</p>

<hr>

<p align="center">
  <b>Built with Python • FastAPI • Streamlit • Gemini • Pinecone •
  FastEmbed • Tavily • Tesseract OCR</b>
</p>

<p align="center">
  🤖 Multi-Agent AI • 📄 Document Intelligence • 📊 Presentation Generation
  • 🔎 Enterprise RAG • 🌐 Web Research
</p>

<hr>

<p align="center">
  Made with ❤️ for the Multi-Agent AI Document & PPT Generation Assignment
</p>