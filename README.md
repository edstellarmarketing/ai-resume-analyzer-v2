# AI Resume Analysis Tool

Analyze resumes against job requirements using Claude AI.

## Features
- Bulk resume analysis (up to 10 files)
- Support for PDF, DOCX, and TXT files
- Duty-based matching algorithm
- Export results to CSV
- Real-time character counting
- Color-coded results

## Live Demo
🚀 **[Try the app here](https://your-app-url.onrender.com)** (will be updated after deployment)

## How It Works
1. Upload resume files (PDF, DOCX, or TXT)
2. Define job title and required duties
3. AI analyzes each resume against job requirements
4. Get color-coded results with detailed matching scores
5. Export results as CSV for further analysis

## Technology Stack
- **Frontend:** Gradio
- **AI:** Claude API (Anthropic)
- **Document Processing:** PyPDF2, python-docx
- **Data:** Pandas
- **Deployment:** Render

## Usage Instructions
1. **Upload Resumes:** Select up to 10 resume files
2. **Job Requirements:** Fill in job title and duties (max 500 chars each)
3. **Analysis:** Click "Analyze Multiple Resumes"
4. **Results:** View color-coded results table
5. **Export:** Download CSV file with all results

## Color Legend
- 🟢 **Good Match** - Candidate's current duties closely match important duties
- 🟠 **Considerable Match** - Candidate's current duties match considerable duties  
- 🔴 **Reject/Error** - Poor match or processing error

## Deployment
This app is deployed on Render with secure environment variable handling for API keys.

## Security
- API keys are stored as environment variables
- No sensitive data is logged or stored
- File processing is done in memory only

## Support
For issues or questions, please create an issue in this repository.
