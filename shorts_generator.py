on:
  schedule:
    # Runs every day at 2 AM UTC
    - cron: '0 2 * * *'
  # Also allow manual trigger
  workflow_dispatch:
 
jobs:
  process_videos:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          sudo apt-get install ffmpeg
      
      - name: Download and process videos
        env:
          SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          YOUTUBE_CREDENTIALS: ${{ secrets.YOUTUBE_CREDENTIALS }}
        run: |
          python shorts_generator.py
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: processed-shorts
          path: output_shorts/
