#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import yt_dlp
import threading
import os
import re
from queue import Queue, Empty
import sys

class YouTubeDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Audio Downloader")
        self.root.geometry("800x700")
        
        # Queue for thread communication
        self.log_queue = Queue()
        self.download_thread = None
        
        self.setup_ui()
        self.check_log_queue()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # URL input
        ttk.Label(main_frame, text="YouTube URL or Playlist:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(main_frame, width=60)
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        
        # Download type selection
        ttk.Label(main_frame, text="Download Type:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.download_type = tk.StringVar(value="single")
        type_frame = ttk.Frame(main_frame)
        type_frame.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))
        ttk.Radiobutton(type_frame, text="Single Video", variable=self.download_type, value="single").pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(type_frame, text="Playlist", variable=self.download_type, value="playlist").pack(side=tk.LEFT)
        
        # Quality selection
        ttk.Label(main_frame, text="Audio Quality:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.quality_mode = tk.StringVar(value="best")
        quality_frame = ttk.Frame(main_frame)
        quality_frame.grid(row=2, column=1, sticky=tk.W, pady=(0, 5))
        ttk.Radiobutton(quality_frame, text="Best", variable=self.quality_mode, value="best").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(quality_frame, text="Worst", variable=self.quality_mode, value="worst").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(quality_frame, text="Custom", variable=self.quality_mode, value="specific").pack(side=tk.LEFT)
        
        # Custom bitrate input
        ttk.Label(main_frame, text="Target Bitrate (for Custom):").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.bitrate_entry = ttk.Entry(main_frame, width=20)
        self.bitrate_entry.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))
        self.bitrate_entry.insert(0, "192k")
        
        # MP3 Quality
        ttk.Label(main_frame, text="MP3 Quality:").grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        self.mp3_quality = tk.StringVar(value="192")
        quality_combo = ttk.Combobox(main_frame, textvariable=self.mp3_quality, width=10, state="readonly")
        quality_combo['values'] = ("128", "192", "256", "320")
        quality_combo.grid(row=4, column=1, sticky=tk.W, pady=(0, 5))
        
        # Output directory
        ttk.Label(main_frame, text="Output Directory:").grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=5, column=1, sticky="ew", pady=(0, 5))
        output_frame.columnconfigure(0, weight=1)
        
        self.output_path = tk.StringVar(value=os.getcwd())
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_path)
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(output_frame, text="Browse", command=self.browse_directory).grid(row=0, column=1)
        
        # Progress bar
        ttk.Label(main_frame, text="Progress:").grid(row=6, column=0, sticky=tk.W, pady=(20, 5))
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=1, sticky="ew", pady=(20, 5))
        
        # Download button
        self.download_btn = ttk.Button(main_frame, text="Download", command=self.start_download)
        self.download_btn.grid(row=7, column=1, pady=(10, 0), sticky=tk.W)
        
        # Log area
        ttk.Label(main_frame, text="Log:").grid(row=8, column=0, sticky="nw", pady=(20, 0))
        self.log_text = scrolledtext.ScrolledText(main_frame, height=15, width=80)
        self.log_text.grid(row=8, column=1, sticky="nsew", pady=(20, 0))
        
        # Configure grid weights for resizing
        main_frame.rowconfigure(8, weight=1)
        
    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.output_path.get())
        if directory:
            self.output_path.set(directory)
    
    def log_message(self, message):
        """Add message to log queue for thread-safe logging"""
        self.log_queue.put(message)
    
    def check_log_queue(self):
        """Check for new log messages and display them"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.root.update_idletasks()
        except Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.check_log_queue)
    
    def parse_bitrate(self, bitrate_str):
        """Converts bitrate string like '128k' to integer 128."""
        if isinstance(bitrate_str, (int, float)):
            return int(bitrate_str)
        if isinstance(bitrate_str, str):
            val = re.match(r"(\d+)", bitrate_str)
            if val:
                return int(val.group(1))
        return 0
    
    def fetch_audio_formats(self, video_url):
        """Fetch available audio formats for a video"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
        }
        processed_formats = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(video_url, download=False)
                formats = info_dict.get('formats', [])
                for f in formats:
                    if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                        processed_formats.append({
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'abr': f.get('abr'),
                            'acodec': f.get('acodec'),
                            'filesize': f.get('filesize'),
                            'filesize_approx': f.get('filesize_approx')
                        })
            processed_formats.sort(key=lambda x: (x.get('abr') or 0), reverse=True)
            return processed_formats
        except Exception as e:
            self.log_message(f"Error fetching video information: {e}")
            return None
    
    def select_format_best(self, audio_formats):
        """Select the best quality format"""
        if not audio_formats:
            return None
        valid_formats = [f for f in audio_formats if f.get('abr') is not None]
        if not valid_formats:
            return audio_formats[0] if audio_formats else None
        return valid_formats[0]
    
    def select_format_worst(self, audio_formats):
        """Select the worst quality format"""
        if not audio_formats:
            return None
        valid_formats = [f for f in audio_formats if f.get('abr') is not None]
        if not valid_formats:
            return audio_formats[-1] if audio_formats else None
        valid_formats.sort(key=lambda x: (x.get('abr') or float('inf')))
        return valid_formats[0]
    
    def select_format_specific(self, audio_formats, target_bitrate_str):
        """Select format matching specific bitrate"""
        if not audio_formats:
            return None
        target_abr = self.parse_bitrate(target_bitrate_str)
        if target_abr == 0:
            self.log_message(f"Invalid target bitrate: {target_bitrate_str}")
            return None
        
        formats_with_abr = [f for f in audio_formats if f.get('abr') is not None]
        if not formats_with_abr:
            self.log_message("No formats found with bitrate information.")
            return audio_formats[0]
        
        exact_match = None
        higher_matches = []
        lower_matches = []
        
        for f in formats_with_abr:
            if f['abr'] == target_abr:
                exact_match = f
                break
            elif f['abr'] > target_abr:
                higher_matches.append(f)
            else:
                lower_matches.append(f)
        
        if exact_match:
            return exact_match
        
        if higher_matches:
            higher_matches.sort(key=lambda x: x['abr'])
            return higher_matches[0]
        
        if lower_matches:
            lower_matches.sort(key=lambda x: x['abr'], reverse=True)
            return lower_matches[0]
        
        return formats_with_abr[0] if formats_with_abr else None
    
    def get_playlist_urls(self, playlist_url):
        """Extract individual video URLs from a playlist"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(playlist_url, download=False)
                if 'entries' in info_dict:
                    urls = []
                    for entry in info_dict['entries']:
                        if entry:
                            url = entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}"
                            urls.append(url)
                    return urls
                else:
                    # Single video, not a playlist
                    return [playlist_url]
        except Exception as e:
            self.log_message(f"Error extracting playlist: {e}")
            return None
    
    def download_single_video(self, video_url, output_path, mp3_quality):
        """Download a single video"""
        try:
            self.log_message(f"Processing: {video_url}")
            
            # Fetch available formats
            audio_formats = self.fetch_audio_formats(video_url)
            if not audio_formats:
                self.log_message("No audio formats found for this video")
                return False
            
            # Select format based on quality mode
            quality_mode = self.quality_mode.get()
            if quality_mode == "best":
                selected_format = self.select_format_best(audio_formats)
            elif quality_mode == "worst":
                selected_format = self.select_format_worst(audio_formats)
            elif quality_mode == "specific":
                target_bitrate = self.bitrate_entry.get()
                selected_format = self.select_format_specific(audio_formats, target_bitrate)
            else:
                selected_format = self.select_format_best(audio_formats)
            
            if not selected_format:
                self.log_message("No suitable format found")
                return False
            
            self.log_message(f"Selected format: {selected_format.get('ext')} - {selected_format.get('abr')}k")
            
            # Download and convert
            format_id = selected_format.get('format_id')
            ydl_opts = {
                'quiet': False,
                'no_warnings': True,
                'format': format_id,
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': mp3_quality,
                }],
                'keepvideo': False,
                'noplaylist': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            self.log_message("Download completed successfully")
            return True
            
        except Exception as e:
            self.log_message(f"Error downloading video: {e}")
            return False
    
    def download_worker(self):
        """Worker function for download thread"""
        try:
            url = self.url_entry.get().strip()
            if not url:
                self.log_message("Please enter a YouTube URL")
                return
            
            output_path = self.output_path.get()
            mp3_quality = self.mp3_quality.get()
            download_type = self.download_type.get()
            
            self.log_message(f"Starting download...")
            self.log_message(f"Output directory: {output_path}")
            self.log_message(f"MP3 quality: {mp3_quality}k")
            
            if download_type == "playlist":
                # Handle playlist
                self.log_message("Extracting playlist URLs...")
                urls = self.get_playlist_urls(url)
                if not urls:
                    self.log_message("Failed to extract playlist URLs")
                    return
                
                self.log_message(f"Found {len(urls)} videos in playlist")
                
                successful = 0
                for i, video_url in enumerate(urls, 1):
                    self.log_message(f"\n--- Downloading {i}/{len(urls)} ---")
                    if self.download_single_video(video_url, output_path, mp3_quality):
                        successful += 1
                
                self.log_message(f"\nPlaylist download completed: {successful}/{len(urls)} successful")
            else:
                # Handle single video
                self.download_single_video(url, output_path, mp3_quality)
            
        except Exception as e:
            self.log_message(f"Download error: {e}")
        finally:
            # Re-enable download button and stop progress bar
            self.root.after(0, self.download_finished)
    
    def download_finished(self):
        """Called when download is finished"""
        self.progress.stop()
        self.download_btn.config(state='normal', text='Download')
        self.log_message("\n--- Download process finished ---\n")
    
    def start_download(self):
        """Start the download process in a separate thread"""
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning("Download in Progress", "A download is already in progress")
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Start progress bar and disable button
        self.progress.start()
        self.download_btn.config(state='disabled', text='Downloading...')
        
        # Start download thread
        self.download_thread = threading.Thread(target=self.download_worker)
        self.download_thread.daemon = True
        self.download_thread.start()

def main():
    root = tk.Tk()
    app = YouTubeDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()