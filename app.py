import gradio as gr
import anthropic
import PyPDF2
import docx
import pandas as pd
import re
import os
from datetime import datetime

# Secure API key handling
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY')

def extract_text_from_file(file):
    if file is None:
        return ""
    
    file_extension = file.name.lower().split('.')[-1]
    
    try:
        if file_extension == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        
        elif file_extension in ['docx', 'doc']:
            doc = docx.Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        elif file_extension == 'txt':
            return file.read().decode('utf-8')
        
        else:
            return f"Unsupported file format: {file.name}"
    
    except Exception as e:
        return f"Error reading {file.name}: {str(e)}"

def analyze_single_resume(client, resume_text, job_title, important_duties, considerable_duties, filename):
    prompt = f"""You are an expert HR analyst. Please analyze this candidate's resume against the job requirements and extract specific information.

JOB TITLE: {job_title}

IMPORTANT DUTIES CANDIDATE SHOULD HANDLE:
{important_duties}

CONSIDERABLE DUTIES CANDIDATE SHOULD HANDLE:
{considerable_duties}

CANDIDATE RESUME:
{resume_text}

ANALYSIS INSTRUCTIONS:
1. Extract candidate's personal and professional information
2. Identify candidate's CURRENT job duties and responsibilities from their resume
3. For CURRENT_COMPANY and CURRENT_DESIGNATION, look for:
   - Jobs with "Present", "Current", or the current year (2024/2025) as end date
   - The most recent position that is still ongoing
   - If multiple current positions, choose the primary/main one
4. Compare candidate's CURRENT job duties with the Important Duties and Considerable Duties
5. Apply the following matching logic:
   - If candidate's CURRENT duties closely match Important Duties → "GOOD MATCH"
   - If candidate's CURRENT duties closely match Considerable Duties → "CONSIDERABLE MATCH"  
   - If candidate's CURRENT duties don't match either Important or Considerable Duties → "REJECT"

IMPORTANT: Pay special attention to date ranges. "2024-Present", "2024-Current", or similar patterns indicate the CURRENT position.

Please provide your analysis in the following EXACT format:

CANDIDATE_NAME: [Extract full name]
EMAIL: [Extract email address]
PHONE: [Extract phone number]
CURRENT_COMPANY: [Extract CURRENT/most recent ongoing company name - look for "Present" or current year]
CURRENT_DESIGNATION: [Extract CURRENT/most recent ongoing job title - look for "Present" or current year]
TOTAL_EXPERIENCE: [Extract total years of experience across all positions]
MATCH_SCORE: [Rate 1-10 how well candidate's CURRENT duties match job requirements]
RECOMMENDATION: [Either "GOOD MATCH" or "CONSIDERABLE MATCH" or "REJECT" based on CURRENT role duties]
REASON: [One sentence explaining your decision based on CURRENT job duty matching]

If any information is not available in the resume, write "Not Available" for that field."""
    
    try:
        message = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        analysis_text = message.content[0].text
        
        candidate_data = {
            "Name": "Not Available",
            "Email": "Not Available", 
            "Phone": "Not Available",
            "Current Company Name": "Not Available",
            "Current Designation": "Not Available",
            "Total Exp": "Not Available",
            "Match Score": "Not Available",
            "Recommendation": "Not Available",
            "Reason": "Not Available",
            "File Name": filename
        }
        
        patterns = {
            "Name": r"CANDIDATE_NAME:\s*(.+)",
            "Email": r"EMAIL:\s*(.+)",
            "Phone": r"PHONE:\s*(.+)",
            "Current Company Name": r"CURRENT_COMPANY:\s*(.+)",
            "Current Designation": r"CURRENT_DESIGNATION:\s*(.+)",
            "Total Exp": r"TOTAL_EXPERIENCE:\s*(.+)",
            "Match Score": r"MATCH_SCORE:\s*(.+)",
            "Recommendation": r"RECOMMENDATION:\s*(.+)",
            "Reason": r"REASON:\s*(.+)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, analysis_text, re.IGNORECASE)
            if match:
                candidate_data[key] = match.group(1).strip()
        
        return candidate_data
        
    except Exception as e:
        return {
            "Name": "Error",
            "Email": "Error",
            "Phone": "Error",
            "Current Company Name": "Error",
            "Current Designation": "Error",
            "Total Exp": "Error",
            "Match Score": "Error",
            "Recommendation": "Error",
            "Reason": f"API Error: {str(e)}",
            "File Name": filename
        }

def add_color_indicators(df):
    """Add color indicators to File Name based on Recommendation"""
    df_colored = df.copy()
    
    for idx, row in df_colored.iterrows():
        recommendation = str(row['Recommendation']).upper()
        filename = str(row['File Name'])
        
        if 'GOOD MATCH' in recommendation:
            df_colored.at[idx, 'File Name'] = f"🟢 {filename}"
        elif 'CONSIDERABLE MATCH' in recommendation:
            df_colored.at[idx, 'File Name'] = f"🟠 {filename}"
        elif 'REJECT' in recommendation or 'ERROR' in recommendation:
            df_colored.at[idx, 'File Name'] = f"🔴 {filename}"
        else:
            df_colored.at[idx, 'File Name'] = f"⚪ {filename}"
    
    return df_colored

def analyze_multiple_resumes(resume_files, job_title, important_duties, considerable_duties, existing_data):
    # Check if API key is available
    if not CLAUDE_API_KEY:
        error_df = pd.DataFrame({
            "Error": ["⚠️ API Key not configured. Please contact administrator."]
        })
        return error_df, None, gr.update(visible=False)
    
    if not resume_files or len(resume_files) == 0:
        return existing_data, None, gr.update(visible=False)
    
    if len(resume_files) > 10:
        return pd.DataFrame({"Error": ["Maximum 10 resume files allowed"]}), None, gr.update(visible=False)
    
    if not job_title.strip():
        return pd.DataFrame({"Error": ["Please enter the job title"]}), None, gr.update(visible=False)
        
    if not important_duties.strip():
        return pd.DataFrame({"Error": ["Please enter the important duties"]}), None, gr.update(visible=False)
        
    if not considerable_duties.strip():
        return pd.DataFrame({"Error": ["Please enter the considerable duties"]}), None, gr.update(visible=False)
    
    if len(important_duties) > 500:
        return pd.DataFrame({"Error": [f"Important Duties exceeds 500 characters. Current: {len(important_duties)} characters"]}), None, gr.update(visible=False)
        
    if len(considerable_duties) > 500:
        return pd.DataFrame({"Error": [f"Considerable Duties exceeds 500 characters. Current: {len(considerable_duties)} characters"]}), None, gr.update(visible=False)
    
    try:
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    except Exception as e:
        return pd.DataFrame({"Error": [f"Error initializing Claude API: {str(e)}"]}), None, gr.update(visible=False)
    
    all_candidates = []
    
    # Add existing data if any
    if existing_data is not None and not existing_data.empty:
        # Remove color indicators from existing data for processing
        existing_clean = existing_data.copy()
        if 'File Name' in existing_clean.columns:
            for idx, row in existing_clean.iterrows():
                filename = str(row['File Name'])
                clean_filename = re.sub(r'^[🟢🟠🔴⚪] ', '', filename)
                existing_clean.at[idx, 'File Name'] = clean_filename
        all_candidates.extend(existing_clean.to_dict('records'))
    
    for resume_file in resume_files:
        resume_text = extract_text_from_file(resume_file)
        filename = os.path.basename(resume_file.name)
        
        if resume_text.startswith("Error") or resume_text.startswith("Unsupported"):
            error_data = {
                "Name": "File Error",
                "Email": "N/A",
                "Phone": "N/A",
                "Current Company Name": "N/A",
                "Current Designation": "N/A",
                "Total Exp": "N/A",
                "Match Score": "N/A",
                "Recommendation": "ERROR",
                "Reason": resume_text,
                "File Name": filename
            }
            all_candidates.append(error_data)
        else:
            candidate_data = analyze_single_resume(client, resume_text, job_title, important_duties, considerable_duties, filename)
            all_candidates.append(candidate_data)
    
    df = pd.DataFrame(all_candidates)
    
    column_order = ["File Name", "Name", "Email", "Phone", "Current Company Name", 
                   "Current Designation", "Total Exp", "Match Score", "Recommendation", "Reason"]
    df = df[column_order]
    
    # Add color indicators
    df = add_color_indicators(df)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"resume_analysis_{timestamp}.csv"
    
    # Create clean version for CSV (without emoji indicators)
    df_for_csv = df.copy()
    for idx, row in df_for_csv.iterrows():
        filename = str(row['File Name'])
        # Remove emoji indicators for CSV
        clean_filename = re.sub(r'^[🟢🟠🔴⚪] ', '', filename)
        df_for_csv.at[idx, 'File Name'] = clean_filename
    
    df_for_csv.to_csv(csv_filename, index=False)
    
    # Show the "Upload More Resumes" section after first analysis
    return df, csv_filename, gr.update(visible=True)

def show_analyze_button(files):
    """Show or hide the analyze button based on file upload"""
    if files is not None and len(files) > 0:
        return gr.update(visible=True)
    else:
        return gr.update(visible=False)

def update_important_char_count_and_button(text, considerable_text):
    char_count = len(text)
    considerable_count = len(considerable_text) if considerable_text else 0
    
    button_interactive = char_count <= 500 and considerable_count <= 500
    
    if char_count > 500:
        char_display = f"⚠️ {char_count}/500 characters (Exceeds limit!)"
    else:
        char_display = f"✅ {char_count}/500 characters"
    
    return char_display, gr.update(interactive=button_interactive), gr.update(interactive=button_interactive)

def update_considerable_char_count_and_button(text, important_text):
    char_count = len(text)
    important_count = len(important_text) if important_text else 0
    
    button_interactive = char_count <= 500 and important_count <= 500
    
    if char_count > 500:
        char_display = f"⚠️ {char_count}/500 characters (Exceeds limit!)"
    else:
        char_display = f"✅ {char_count}/500 characters"
    
    return char_display, gr.update(interactive=button_interactive), gr.update(interactive=button_interactive)

def clear_all():
    return [], [], "", "", "", pd.DataFrame(), None, "✅ 0/500 characters", "✅ 0/500 characters", gr.update(interactive=True), gr.update(visible=False), gr.update(visible=False)

def show_api_status():
    """Show API configuration status"""
    if CLAUDE_API_KEY:
        return "🟢 API Key Configured"
    else:
        return "🔴 API Key Not Configured"

# Simple CSS for professional look
css = """
.dataframe td, .dataframe th {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 200px !important;
}
.dataframe table {
    table-layout: auto !important;
    width: 100% !important;
}
.dataframe {
    max-height: 600px !important;
    overflow-y: auto !important;
}
.quick-analysis-section {
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
    padding: 16px !important;
    margin: 10px 0 !important;
    background-color: #f8fafc !important;
}
.quick-analysis-section .wrap {
    background: transparent !important;
}
.api-status {
    padding: 8px;
    border-radius: 4px;
    margin-bottom: 10px;
    text-align: center;
    font-weight: bold;
}
"""

# Create the interface
def create_interface():
    with gr.Blocks(title="Resume Analysis Tool - Duty-Based Matching", css=css) as interface:
        gr.Markdown("# Resume Analysis Tool - Duty-Based Matching")
        gr.Markdown("Upload resumes (bulk or individual) and define job requirements for structured analysis")
        
        # API Status indicator
        api_status = gr.Markdown(show_api_status(), elem_classes=["api-status"])
        
        with gr.Row():
            with gr.Column():            
                resume_files_input = gr.File(
                    label="Upload Multiple Resumes (PDF, DOCX, TXT) - Max 10 files", 
                    file_types=[".pdf", ".docx", ".txt"],
                    file_count="multiple"
                )
                
                job_title_input = gr.Textbox(
                    label="Job Title",
                    placeholder="e.g., Senior Software Engineer, Sales Manager, etc.",
                    lines=1
                )
                
                with gr.Column():
                    important_duties_input = gr.Textbox(
                        label="Important Duties Candidate Should Handle (Max 500 characters)",
                        placeholder="List the most critical responsibilities and duties for this role...",
                        lines=5,
                        max_lines=5
                    )
                    important_char_count = gr.Markdown("✅ 0/500 characters")
                
                with gr.Column():
                    considerable_duties_input = gr.Textbox(
                        label="Considerable Duties Candidate Should Handle (Max 500 characters)",
                        placeholder="List additional important but secondary duties for this role...",
                        lines=5,
                        max_lines=5
                    )
                    considerable_char_count = gr.Markdown("✅ 0/500 characters")
                
                with gr.Row():
                    analyze_bulk_btn = gr.Button(
                        "Analyze Multiple Resumes", 
                        variant="primary",
                        interactive=bool(CLAUDE_API_KEY)
                    )
                
                with gr.Row():
                    clear_btn = gr.Button("Clear All", variant="stop")
                
                gr.Markdown("### Instructions:")
                gr.Markdown("1. Upload resume files and define job requirements")
                gr.Markdown("2. Click 'Analyze Multiple Resumes' to start")
                gr.Markdown("3. Use 'Quick Continue Analysis' section for additional resumes")
                gr.Markdown("### Note:")
                gr.Markdown("- Additional resumes will be added to existing analysis results")
                gr.Markdown("- Analysis buttons are disabled if character limits are exceeded")
                
                if not CLAUDE_API_KEY:
                    gr.Markdown("### ⚠️ Configuration Required:")
                    gr.Markdown("API key is not configured. Please contact the administrator to set up the ANTHROPIC_API_KEY environment variable.")
            
            with gr.Column():
                results_output = gr.Dataframe(
                    label="Analysis Results for All Candidates",
                    interactive=False
                )
                
                csv_download = gr.File(
                    label="Download Results as CSV",
                    visible=False
                )
                
                # Quick Analysis Section (positioned below the table)
                with gr.Group(visible=False, elem_classes=["quick-analysis-section"]) as upload_more_section:
                    gr.Markdown("**Quick Continue Analysis**")
                    additional_resume_input = gr.File(
                        label="Upload More Resumes (Max 10)", 
                        file_types=[".pdf", ".docx", ".txt"],
                        file_count="multiple"
                    )
                    
                    analyze_more_resumes_btn = gr.Button(
                        "Analyze More Resumes", 
                        variant="secondary", 
                        visible=False,
                        interactive=bool(CLAUDE_API_KEY)
                    )
                    
                    gr.Markdown("*This section uses the same job requirements as above*")
                
                gr.Markdown("### Export Results:")
                gr.Markdown("- After analysis, you can download the results as a CSV file")
                gr.Markdown("- You can also copy the table data or take a screenshot")
                gr.Markdown("### Color Legend:")
                gr.Markdown("- 🟢 **Good Match**")
                gr.Markdown("- 🟠 **Considerable Match**")
                gr.Markdown("- 🔴 **Reject/Error**")
                gr.Markdown("### Note:")
                gr.Markdown("- Hover over cells to see full text content")
        
        # Event handlers
        if CLAUDE_API_KEY:
            # Show/hide the "Analyze More Resumes" button when additional files are uploaded
            additional_resume_input.change(
                fn=show_analyze_button,
                inputs=[additional_resume_input],
                outputs=[analyze_more_resumes_btn]
            )
            
            important_duties_input.change(
                fn=update_important_char_count_and_button,
                inputs=[important_duties_input, considerable_duties_input],
                outputs=[important_char_count, analyze_bulk_btn, analyze_more_resumes_btn]
            )
            
            considerable_duties_input.change(
                fn=update_considerable_char_count_and_button,
                inputs=[considerable_duties_input, important_duties_input],
                outputs=[considerable_char_count, analyze_bulk_btn, analyze_more_resumes_btn]
            )
            
            analyze_bulk_btn.click(
                fn=analyze_multiple_resumes,
                inputs=[resume_files_input, job_title_input, important_duties_input, considerable_duties_input, results_output],
                outputs=[results_output, csv_download, upload_more_section]
            ).then(
                fn=lambda csv_file: gr.update(visible=True) if csv_file else gr.update(visible=False),
                inputs=[csv_download],
                outputs=[csv_download]
            )
            
            analyze_more_resumes_btn.click(
                fn=analyze_multiple_resumes,
                inputs=[additional_resume_input, job_title_input, important_duties_input, considerable_duties_input, results_output],
                outputs=[results_output, csv_download, upload_more_section]
            ).then(
                fn=lambda csv_file: gr.update(visible=True) if csv_file else gr.update(visible=False),
                inputs=[csv_download],
                outputs=[csv_download]
            )
        
        clear_btn.click(
            fn=clear_all,
            outputs=[resume_files_input, additional_resume_input, job_title_input, important_duties_input, considerable_duties_input, results_output, csv_download, important_char_count, considerable_char_count, analyze_bulk_btn, upload_more_section, analyze_more_resumes_btn]
        )
    
    return interface

# Create and launch the interface
if __name__ == "__main__":
    interface = create_interface()
    
    # Get port from environment variable (Render requirement)
    port = int(os.environ.get("PORT", 7860))
    
    interface.launch(
        server_name="0.0.0.0",  # Required for external access
        server_port=port,        # Use Render's assigned port
        share=False             # Render handles public access
    )
