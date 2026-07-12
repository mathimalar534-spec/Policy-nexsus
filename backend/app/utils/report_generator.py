import json
import csv
import os
import logging
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.models import Finding, Policy, Obligation
from app.dashboard.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

class ReportGenerator:
    @classmethod
    def generate_json_report(cls, db: Session, file_path: str) -> str:
        findings = db.query(Finding).all()
        data = []
        for f in findings:
            pol_a = db.query(Policy).filter(Policy.id == f.policy_a_id).first() if f.policy_a_id else None
            pol_b = db.query(Policy).filter(Policy.id == f.policy_b_id).first() if f.policy_b_id else None
            pol = db.query(Policy).filter(Policy.id == f.policy_id).first() if f.policy_id else None
            
            data.append({
                "id": f.id,
                "type": f.finding_type,
                "subtype": f.finding_subtype,
                "severity": f.severity,
                "confidence": f.confidence,
                "policy_a": pol_a.title if pol_a else None,
                "policy_b": pol_b.title if pol_b else None,
                "policy": pol.title if pol else None,
                "description": f.description,
                "explanation": f.explanation,
                "recommendation": f.recommendation,
                "created_at": f.created_at.isoformat()
            })
            
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return file_path

    @classmethod
    def generate_csv_report(cls, db: Session, file_path: str) -> str:
        findings = db.query(Finding).all()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Type", "Subtype", "Severity", "Confidence", 
                "Policy A / Policy", "Policy B", "Description", "Explanation", "Recommendation"
            ])
            
            for fi in findings:
                pol_a = db.query(Policy).filter(Policy.id == fi.policy_a_id).first() if fi.policy_a_id else None
                pol_b = db.query(Policy).filter(Policy.id == fi.policy_b_id).first() if fi.policy_b_id else None
                pol = db.query(Policy).filter(Policy.id == fi.policy_id).first() if fi.policy_id else None
                
                pol_a_str = pol_a.title if pol_a else (pol.title if pol else "")
                pol_b_str = pol_b.title if pol_b else ""
                
                writer.writerow([
                    fi.id, fi.finding_type, fi.finding_subtype, fi.severity, fi.confidence,
                    pol_a_str, pol_b_str, fi.description, fi.explanation, fi.recommendation
                ])
        return file_path

    @classmethod
    def generate_pdf_report(cls, db: Session, file_path: str) -> str:
        """
        Generates an enterprise-ready PDF document summarizing the findings
        using ReportLab library.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            
            # Setup document
            doc = SimpleDocTemplate(file_path, pagesize=letter, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
            story = []
            
            # Styles
            styles = getSampleStyleSheet()
            
            # Custom styled palette
            primary_color = colors.HexColor("#1A2B4C")    # Navy Slate
            secondary_color = colors.HexColor("#3F5D7D")  # Blue Grey
            accent_color = colors.HexColor("#A8201A")     # Rust Dark Red
            text_color = colors.HexColor("#2B2D42")       # Charcoal
            
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=26,
                textColor=primary_color,
                leading=32,
                spaceAfter=15
            )
            
            h1_style = ParagraphStyle(
                'Heading1_Custom',
                fontName='Helvetica-Bold',
                fontSize=18,
                textColor=primary_color,
                leading=22,
                spaceBefore=15,
                spaceAfter=10
            )

            h2_style = ParagraphStyle(
                'Heading2_Custom',
                fontName='Helvetica-Bold',
                fontSize=14,
                textColor=secondary_color,
                leading=18,
                spaceBefore=10,
                spaceAfter=6
            )
            
            body_style = ParagraphStyle(
                'BodyText_Custom',
                fontName='Helvetica',
                fontSize=10,
                textColor=text_color,
                leading=14,
                spaceAfter=8
            )

            table_body_style = ParagraphStyle(
                'TableBody',
                fontName='Helvetica',
                fontSize=8,
                textColor=text_color,
                leading=10
            )

            table_header_style = ParagraphStyle(
                'TableHeader',
                fontName='Helvetica-Bold',
                fontSize=9,
                textColor=colors.white,
                leading=11
            )
            
            # 1. Cover Page / Header
            story.append(Paragraph("Enterprise Policy Compliance Report", title_style))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
            story.append(Paragraph("Target System: Fortune 500 Central Policy Repository", body_style))
            story.append(Spacer(1, 0.25 * inch))
            
            # Calculate Risk / Governance score
            risk_metrics = RiskEngine.calculate_governance_score(db)
            score = risk_metrics["governance_score"]
            grade = risk_metrics["grade"]
            
            # Score Table
            score_data = [
                [Paragraph("Governance Metric", table_header_style), Paragraph("Value / Grade", table_header_style)],
                [Paragraph("Compliance Score", table_body_style), Paragraph(f"<b>{score} / 100</b>", table_body_style)],
                [Paragraph("Security Risk Level", table_body_style), Paragraph(f"<b>{grade}</b>", table_body_style)]
            ]
            score_table = Table(score_data, colWidths=[2.5 * inch, 3.5 * inch])
            score_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), primary_color),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('TOPPADDING', (0,0), (-1,0), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D1D5DB")),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F9FAFB"), colors.white]),
                ('PADDING', (0,0), (-1,-1), 8)
            ]))
            story.append(score_table)
            story.append(Spacer(1, 0.3 * inch))
            
            # 2. Executive Summary
            story.append(Paragraph("Executive Summary", h1_style))
            summary_text = (
                "This automated governance report evaluates organizational policies to detect overlapping definitions, "
                "regulatory contradictions (direct/partial conflicts), and redundant passages. Additionally, "
                "the scan checks policy freshness dates and references to legacy/insecure technologies (e.g. SSL, SHA1). "
                "Immediate resolution of critical conflicts is recommended to prevent operational failures or regulatory audit penalties."
            )
            story.append(Paragraph(summary_text, body_style))
            story.append(Spacer(1, 0.2 * inch))
            
            # 3. Findings Table
            story.append(Paragraph("Detailed Compliance Findings", h1_style))
            
            findings = db.query(Finding).all()
            if not findings:
                story.append(Paragraph("No conflicts or staleness issues detected. System compliant.", body_style))
            else:
                table_data = [
                    [
                        Paragraph("ID", table_header_style),
                        Paragraph("Type", table_header_style),
                        Paragraph("Severity", table_header_style),
                        Paragraph("Target / Source", table_header_style),
                        Paragraph("Issue Summary", table_header_style)
                    ]
                ]
                
                for f in findings:
                    pol_a = db.query(Policy).filter(Policy.id == f.policy_a_id).first() if f.policy_a_id else None
                    pol_b = db.query(Policy).filter(Policy.id == f.policy_b_id).first() if f.policy_b_id else None
                    pol = db.query(Policy).filter(Policy.id == f.policy_id).first() if f.policy_id else None
                    
                    target = ""
                    if pol_a and pol_b:
                        target = f"{pol_a.title} &<br/>{pol_b.title}"
                    elif pol:
                        target = pol.title
                        
                    severity_color = accent_color if f.severity in ["CRITICAL", "HIGH"] else (colors.HexColor("#F59E0B") if f.severity == "MEDIUM" else text_color)
                    
                    sev_p = Paragraph(f"<font color='{severity_color}'><b>{f.severity}</b></font>", table_body_style)
                    
                    table_data.append([
                        Paragraph(str(f.id), table_body_style),
                        Paragraph(f.finding_subtype, table_body_style),
                        sev_p,
                        Paragraph(target, table_body_style),
                        Paragraph(f.description, table_body_style)
                    ])
                    
                findings_table = Table(table_data, colWidths=[0.4*inch, 1.2*inch, 0.8*inch, 1.8*inch, 2.8*inch])
                findings_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), secondary_color),
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
                    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F3F4F6"), colors.white]),
                    ('PADDING', (0,0), (-1,-1), 6)
                ]))
                story.append(findings_table)
                
            story.append(Spacer(1, 0.3 * inch))
            
            # 4. Remediation Recommendations
            story.append(Paragraph("Remediation Recommendations", h1_style))
            
            high_findings = [f for f in findings if f.severity in ["CRITICAL", "HIGH"]]
            stale_findings = [f for f in findings if f.finding_type == "STALE"]
            
            if high_findings:
                story.append(Paragraph("<b>Resolve High Severity Conflicts First:</b>", h2_style))
                story.append(Paragraph(
                    "Assign a primary risk owner to consolidate policy conflicts. Revise overlapping obligations "
                    "to remove conflicting instructions between different departments.", body_style
                ))
            if stale_findings:
                story.append(Paragraph("<b>Refresh Outdated References:</b>", h2_style))
                story.append(Paragraph(
                    "Re-evaluate policies referencing legacy cryptographic mechanisms (e.g. SHA-1, WEP) and "
                    "update references to specify modern secure defaults (e.g. SHA-256, WPA3).", body_style
                ))
            if not findings:
                story.append(Paragraph("No remediation actions required at this time.", body_style))
                
            # Build PDF
            doc.build(story)
            logger.info(f"PDF report generated at {file_path}")
            
        except Exception as e:
            # Fallback simple text-based report to ensure it doesn't crash if reportlab has issues
            logger.warning(f"ReportLab failed to generate PDF: {str(e)}. Writing plain-text PDF mock.")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"ENTERPRISE POLICY COMPLIANCE REPORT\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                f.write(f"Findings summary count: {db.query(Finding).count()}\n")
                
        return file_path
