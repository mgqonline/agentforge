import pandas as pd
import docx
from fpdf import FPDF
import numpy as np

print("🚀 开始生成高复杂度、多维度的企业级测试文档...\n")

# ==========================================
# 1. 生成极度复杂的 Word: 包含段落、多级标题、表格、加粗
# ==========================================
print("正在生成 Complex_Labor_Contract.docx ...")
doc = docx.Document()

doc.add_heading('Enterprise Master Service Agreement 2026', 0)
doc.add_paragraph('This document is highly confidential.', style='Intense Quote')

doc.add_heading('1. Background & Scope', level=1)
p = doc.add_paragraph('This agreement establishes the terms for the AI transformation project. ')
p.add_run('The project MUST be delivered by Q4. ').bold = True
p.add_run('Failure to do so will result in a 10% penalty.').italic = True

doc.add_heading('2. Deliverables & Pricing (Table Format)', level=1)
# 插入一个 3x3 的表格
table = doc.add_table(rows=1, cols=3)
table.style = 'Table Grid'
hdr_cells = table.rows[0].cells
hdr_cells[0].text = 'Phase'
hdr_cells[1].text = 'Deliverable'
hdr_cells[2].text = 'Cost (USD)'

records = [
    ('Phase 1', 'RAG Knowledge Base Setup', '$50,000'),
    ('Phase 2', 'Agentic Workflow Orchestration', '$120,000'),
    ('Phase 3', 'Multimodal Model Deployment', '$80,000')
]
for phase, desc, cost in records:
    row_cells = table.add_row().cells
    row_cells[0].text = phase
    row_cells[1].text = desc
    row_cells[2].text = cost

doc.add_heading('3. Legal Clauses', level=1)
doc.add_paragraph('Any dispute shall be resolved via arbitration in San Francisco, CA.', style='List Bullet')
doc.save("Complex_Labor_Contract.docx")

# ==========================================
# 2. 生成多页的 PDF: 包含表格排版、超长段落
# ==========================================
print("正在生成 Complex_Annual_Report.pdf ...")
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Global AI Trends 2026 - Internal Report', border=False, ln=1, align='C')
        self.ln(5)

pdf = PDF()
pdf.add_page()
pdf.set_font("Arial", size=11)

# 超长段落（测试文本切块）
long_text = (
    "In 2026, the landscape of Artificial Intelligence has fundamentally shifted from parameter scaling "
    "to agentic capabilities. Large Language Models (LLMs) are no longer passive query responders; they "
    "are now autonomous orchestrators capable of breaking down complex tasks, searching enterprise knowledge "
    "bases using Retrieval-Augmented Generation (RAG), and executing actions via Model Context Protocol (MCP).\n\n"
    "Our enterprise must adapt to this shift. Traditional software engineering is giving way to prompt engineering "
    "and AI-native system design. The integration of vector databases, such as Pinecone or Milvus, has become "
    "mandatory for maintaining stateful memory across sessions."
)
pdf.multi_cell(0, 8, long_text)
pdf.ln(10)

# PDF 中的伪表格排版 (PDF 解析器最容易在这里把文本全部混在一起)
pdf.set_font("Arial", 'B', 12)
pdf.cell(0, 10, "Table 1: Projected AI Budget Allocation", ln=1)
pdf.set_font("Arial", size=10)
pdf.cell(60, 10, "Department", border=1)
pdf.cell(60, 10, "2025 Budget", border=1)
pdf.cell(60, 10, "2026 Budget", border=1)
pdf.ln()

data = [("R&D", "$12M", "$25M"), ("Marketing", "$5M", "$4M"), ("IT Ops", "$8M", "$15M")]
for row in data:
    pdf.cell(60, 10, row[0], border=1)
    pdf.cell(60, 10, row[1], border=1)
    pdf.cell(60, 10, row[2], border=1)
    pdf.ln()

pdf.output("Complex_Annual_Report.pdf")

# ==========================================
# 3. 生成多维度的 Excel: 包含多 Sheet、空值 NaN、混合类型
# ==========================================
print("正在生成 Complex_Sales_Database.xlsx ...")
# Sheet 1: 正常的复杂销售数据
df_sales = pd.DataFrame({
    'Transaction_ID': ['TX-1001', 'TX-1002', 'TX-1003', 'TX-1004', 'TX-1005'],
    'Product_Category': ['Hardware', 'SaaS', 'SaaS', 'Hardware', 'Services'],
    'Revenue': [12000, 4500, np.nan, 32000, 8000],  # 故意制造空值，考验清洗能力
    'Client': ['Acme Corp', 'Stark Ind', 'Wayne Ent', 'Acme Corp', 'LexCorp'],
    'Date': pd.date_range(start='1/1/2026', periods=5)
})

# Sheet 2: 员工考核表 (带长文本评语)
df_hr = pd.DataFrame({
    'Employee': ['Alice', 'Bob'],
    'Q1_Score': [95, 78],
    'Manager_Review': [
        "Alice is an exceptional engineer. She built the entire RAG pipeline single-handedly.",
        "Bob struggled with the new MCP protocol. Needs further training."
    ]
})

with pd.ExcelWriter("Complex_Sales_Database.xlsx") as writer:
    df_sales.to_excel(writer, sheet_name="Q1_Sales_Transactions", index=False)
    df_hr.to_excel(writer, sheet_name="HR_Reviews", index=False)

print("\n✅ 三份高复杂度、多维度数据的文档已生成完毕！")
