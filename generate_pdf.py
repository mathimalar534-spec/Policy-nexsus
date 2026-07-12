import sys
import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
except ImportError:
    print("Error: reportlab is not installed. Please install it using pip.")
    sys.exit(1)

def build_pdf(file_path):
    # Setup document geometry (A4/Letter aligned)
    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Elegant Color Palette
    primary_color = colors.HexColor("#1A2B4C")    # Navy Blue
    secondary_color = colors.HexColor("#3F5D7D")  # Slate Grey
    accent_color = colors.HexColor("#A8201A")     # Critical Accent Red
    text_color = colors.HexColor("#2B2D42")       # Charcoal Body Text
    success_color = colors.HexColor("#10B981")    # Success Green
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        leading=28,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=secondary_color,
        leading=15,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        textColor=primary_color,
        leading=18,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=secondary_color,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=text_color,
        leading=14,
        spaceAfter=6
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white,
        leading=11
    )
    
    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=text_color,
        leading=11
    )

    table_body_bold_style = ParagraphStyle(
        'TableBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=text_color,
        leading=11
    )

    badge_success_style = ParagraphStyle(
        'BadgeSuccess',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=success_color,
        leading=11
    )

    badge_danger_style = ParagraphStyle(
        'BadgeDanger',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=accent_color,
        leading=11
    )
    
    # --- PAGE 1: ADMINISTRATIVE OVERVIEW & SCOPE ---
    story.append(Paragraph("Policy Nexus Compliance Audit Report", title_style))
    story.append(Paragraph("Automated GRC Contradiction & Compliance Analysis", subtitle_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Scorecard Table
    score_data = [
        [Paragraph("AUDIT PARAMETER", table_header_style), Paragraph("VALUATION / POSTURE STATUS", table_header_style)],
        [Paragraph("Audit Timestamp", table_body_style), Paragraph("7/12/2026, 10:44:39 AM", table_body_bold_style)],
        [Paragraph("Audited Scope", table_body_style), Paragraph("2 core infrastructure & security policy documents", table_body_style)],
        [Paragraph("Overall Risk Index", table_body_style), Paragraph("<b>68 / 100</b>", table_body_bold_style)],
        [Paragraph("Compliance Posture", table_body_style), Paragraph("<font color='#F59E0B'><b>ATTENTION REQUIRED</b></font>", table_body_bold_style)]
    ]
    score_table = Table(score_data, colWidths=[2.5 * inch, 4.5 * inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # Document Health Status Table
    story.append(Paragraph("Document Status & Review Timelines", h1_style))
    health_data = [
        [
            Paragraph("Document Name", table_header_style),
            Paragraph("Review Status", table_header_style),
            Paragraph("Last Reviewed", table_header_style),
            Paragraph("Next Review Date", table_header_style)
        ],
        [
            Paragraph("Password Policy.md", table_body_bold_style),
            Paragraph("OVERDUE", badge_danger_style),
            Paragraph("2021-08-15", table_body_style),
            Paragraph("2022-08-15", table_body_style)
        ],
        [
            Paragraph("Cloud Identity Policy.md", table_body_bold_style),
            Paragraph("WITHIN CYCLE", badge_success_style),
            Paragraph("2026-01-10", table_body_style),
            Paragraph("2027-01-10", table_body_style)
        ]
    ]
    health_table = Table(health_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    health_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    story.append(health_table)
    story.append(Spacer(1, 0.2 * inch))
    
    # Executive Overview Summary
    story.append(Paragraph("Executive Overview", h1_style))
    summary_text = (
        "High-priority password control discrepancies were detected between the general security policy guidelines "
        "and the cloud infrastructure team frameworks. Left unresolved, these contradictions create compliance gaps "
        "and security baseline variances across operational environments."
    )
    story.append(Paragraph(summary_text, body_style))
    
    # --- LOGICAL PAGE BREAK FOR SECTION BOUNDARY ---
    story.append(PageBreak())
    
    # --- PAGE 2: CONTRADICTIONS, REMEDIATIONS & SIGN-OFFS ---
    story.append(Paragraph("Detailed Contradiction Analysis", h1_style))
    story.append(Paragraph("The compliance engine evaluated findings under the industry-standard 5 C's framework (Condition, Criteria, Cause, Consequence, Corrective Action) to structure resolution steps:", body_style))
    story.append(Spacer(1, 0.05 * inch))
    
    # Finding 1
    story.append(Paragraph("Finding 1: PASSWORD ROTATION REQUIREMENT CONFLICT (CRITICAL)", h2_style))
    story.append(Paragraph("<b>1. Condition:</b> <i>Password Policy.md §1.2</i> mandates periodic resets every 90 days. Conversely, <i>Cloud Identity Policy.md §2.2</i> states that password rotation is not required.", body_style))
    story.append(Paragraph("<b>2. Criteria:</b> NIST SP 800-63B guidelines recommend deprecating forced periodic resets to prevent predictable password choices.", body_style))
    story.append(Paragraph("<b>3. Cause:</b> Disconnected GRC review schedules between the general Security Committee and the Cloud Infrastructure Operations team.", body_style))
    story.append(Paragraph("<b>4. Consequence:</b> User password fatigue, resulting in easily guessable credential patterns and increased security vulnerability.", body_style))
    story.append(Paragraph("<b>5. Corrective Action:</b> Deprecate the 90-day rotation cycle in the general Password Policy and transition to passwordless multi-factor authentication (MFA).", body_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Finding 2
    story.append(Paragraph("Finding 2: INCONSISTENT PASSWORD COMPLEXITY MINIMUMS (MEDIUM)", h2_style))
    story.append(Paragraph("<b>1. Condition:</b> <i>Password Policy.md §1.1</i> requires passwords to be at least 12 characters. <i>Cloud Identity Policy.md §2.1</i> mandates a minimum of 14 characters.", body_style))
    story.append(Paragraph("<b>2. Criteria:</b> Corporate security baselines mandate uniform complexity constraints across all active authentication directories.", body_style))
    story.append(Paragraph("<b>3. Cause:</b> Separation of policy ownership; guidelines established independently by regional security teams.", body_style))
    story.append(Paragraph("<b>4. Consequence:</b> Uneven security posture across cloud environments, leaving some directories susceptible to credential-cracking.", body_style))
    story.append(Paragraph("<b>5. Corrective Action:</b> Harmonize the complexity threshold by enforcing the stronger 14-character minimum standard across all systems.", body_style))
    story.append(Spacer(1, 0.1 * inch))
    
    # Remediation action steps
    story.append(Paragraph("Strategic Corrective Action Plan", h1_style))
    story.append(Paragraph("1. Standardize and unify credential policy guidelines globally across all operational teams.", body_style))
    story.append(Paragraph("2. Align the Password Policy rotation frequency directly with modern NIST guidelines (enforcing robust MFA protocols and avoiding arbitrary, time-based resets).", body_style))
    story.append(Spacer(1, 0.05 * inch))
    
    nist_elaborate = (
        "<i>NIST SP 800-63B Guidelines Rationale:</i> Modern security standards (NIST SP 800-63B) strongly recommend "
        "against forced password rotation cycles. Forcing users to change passwords arbitrarily (e.g. every 90 days) "
        "fosters 'user fatigue', leading to predictable password selections (e.g., adding sequential numbers or letters) "
        "which are easily cracked. Moving to phishing-resistant MFA reduces credential theft risks far more effectively "
        "than rotation controls while improving user productivity."
    )
    story.append(Paragraph(nist_elaborate, body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Signature row section
    sig_data = [
        [Paragraph("GRC Compliance Officer Signature", table_body_bold_style), Paragraph("Date of Validation", table_body_bold_style)],
        [Paragraph("<br/><br/>________________________________________", table_body_style), Paragraph("<br/><br/>____________________", table_body_style)]
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('PADDING', (0,0), (-1,-1), 4)
    ]))
    story.append(KeepTogether([sig_table]))
    
    # Build the document
    doc.build(story)
    print(f"Success: PDF report generated successfully at {file_path}")

if __name__ == '__main__':
    output_path = os.path.join(os.path.dirname(__file__), 'policy_audit_report.pdf')
    build_pdf(output_path)
