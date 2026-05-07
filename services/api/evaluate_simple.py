import asyncio
import sys
import os

# Ensure app can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google import genai
from sqlalchemy import select

from app.shared.database import async_session
from app.shared.models import Tender, Bidder, Criterion, IngestFile, OcrBlock
from app.config import settings

async def main(tender_id: str):
    print(f"Running simple evaluation for tender: {tender_id}")
    
    async with async_session() as db:
        # 1. Get tender
        tender = await db.get(Tender, tender_id)
        if not tender:
            print(f"Error: Tender {tender_id} not found")
            return
            
        # 2. Get criteria
        crit_res = await db.execute(select(Criterion).where(Criterion.tender_id == tender_id))
        criteria = crit_res.scalars().all()
        if not criteria:
            print("No criteria found for this tender.")
            return
            
        criteria_list = [f"- {c.text} (Type: {c.type}, Mandatory: {c.mandatory})" for c in criteria]
        criteria_text = "\n".join(criteria_list)
        
        # 3. Get all bidders
        bidder_res = await db.execute(select(Bidder).where(Bidder.tender_id == tender_id))
        bidders = bidder_res.scalars().all()
        
        if not bidders:
            print("No bidders found for this tender.")
            return
            
        print(f"Found {len(bidders)} bidders. Extracting text from database...")
        bidders_data = []
        for b in bidders:
            files_res = await db.execute(select(IngestFile).where(IngestFile.bidder_id == b.id))
            file_ids = [f.id for f in files_res.scalars().all()]
            
            all_text = ""
            if file_ids:
                blocks_res = await db.execute(
                    select(OcrBlock).where(OcrBlock.file_id.in_(file_ids)).order_by(OcrBlock.page_number)
                )
                blocks = blocks_res.scalars().all()
                all_text = "\n".join([block.text for block in blocks])
                
            # Limit text to 20,000 characters per bidder to avoid massive context overload
            bidders_data.append(f"=== BIDDER: {b.name} ===\nTEXT EXTRACTED FROM BID DOCUMENTS:\n{all_text[:20000]}\n")
            
        all_bidders_text = "\n\n".join(bidders_data)
        
        # 4. Formulate the giant prompt
        prompt = f"""You are an expert procurement officer evaluating bidders for a tender. 
Here are the exact tender criteria:
{criteria_text}

Here is the data submitted by each bidder (text extracted from their documents):
{all_bidders_text}

Task:
1. Evaluate all the bidders against the criteria. 
2. Clearly state which bidder is the BEST and WHY. 
3. Summarize your findings in a simple, clean, and easy-to-read format. 
4. Avoid overly technical jargon. Just tell me who wins and why they are the best choice.
"""
        
        print("Sending to Gemini 2.5 Flash for evaluation...\n")
        client = genai.Client(api_key=settings.gemini_api_key)
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            print("="*60)
            print("🎯 EVALUATION RESULT (Simple & Clean)")
            print("="*60)
            print(response.text)
            print("="*60)
        except Exception as e:
            print(f"Error calling Gemini: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python evaluate_simple.py <tender_id>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
