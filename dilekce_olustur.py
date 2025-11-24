# --- 1. YAMA: SQLITE FIX (MUTLAKA EN BAŞTA OLMALI) ---
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# --- 2. KÜTÜPHANELER ---
import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import chromadb
import os

# --- 3. SAYFA AYARLARI ---
st.set_page_config(page_title="Arzuhal.ai | RAG Sistemi", page_icon="⚖️")

# --- 4. PDF SINIFI ---
class PDF(FPDF):
    def header(self):
        font_path = "LiberationSerif-Regular.ttf"
        try:
            if os.path.exists(font_path):
                self.add_font('TimesNew', '', font_path, uni=True)
                self.set_font('TimesNew', '', 10)
            else:
                self.set_font('Arial', '', 10)
        except:
            self.set_font('Arial', '', 10)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        font_path = "LiberationSerif-Regular.ttf"
        if os.path.exists(font_path):
            self.add_font('TimesNew', '', font_path, uni=True)
            self.set_font('TimesNew', '', 8)
        else:
            self.set_font('Arial', '', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

def create_pdf(metin):
    pdf = PDF()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font_path = "LiberationSerif-Regular.ttf"
    if os.path.exists(font_path):
        pdf.add_font('TimesNew', '', font_path, uni=True)
        pdf.set_font('TimesNew', '', 10.5) 
    else:
        pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 5, metin.strip(), align='J')
    return pdf.output(dest='S').encode('latin-1')

# --- 5. RAG SİSTEMİ (CACHE RESOURCE İLE DONDURULMUŞ) ---
# @st.cache_resource sayesinde bu fonksiyon sadece 1 kere çalışır 
# ve veritabanı bağlantısı asla kopmaz.
@st.cache_resource
def get_hukuk_sistemi():
    # İstemciyi başlat
    chroma_client = chromadb.Client()
    
    # Koleksiyonu oluştur (Varsa sil, temiz başla)
    try:
        chroma_client.delete_collection(name="hukuk_kutuphanesi")
    except:
        pass
    
    collection = chroma_client.create_collection(name="hukuk_kutuphanesi")

    # BELGELER (Zenginleştirilmiş Veri Seti)
    documents = [
        """KONU: Gürültü, Komşu, Rahatsızlık, Ses, Matkap, Müzik. 
        İÇERİK: Kiracı veya ev sahibi, bağımsız bölümleri kullanırken doğruluk kurallarına uymak, özellikle birbirini rahatsız etmemek ve gürültü yapmamakla yükümlüdür. Gürültü yapmak tahliye sebebidir. 
        (Kat Mülkiyeti Kanunu Madde 18 - Gürültü Yasağı)""",
        
        """KONU: Kira Zammı, Kira Artışı, Fahiş Fiyat, Yüksek Zam, Ev Sahibi Zam İstiyor, Enflasyon.
        İÇERİK: Konut kiralarında kira bedeli artışı, bir önceki kira yılındaki TÜFE (On iki aylık ortalama) oranını geçemez. Ev sahibi keyfi olarak %100 veya fahiş zam yapamaz. Yasal sınır TÜFE'dir.
        (TBK Madde 344 - Kira Belirleme)""",
        
        """KONU: Evden Çıkarma, Tahliye Taahhütnamesi, Ev Sahibi Çık Diyor, Oğlum Gelecek.
        İÇERİK: Kiraya veren, gereksinim amacıyla (oğlum oturacak vb.) kiralananın boşaltılmasını sağladığında, haklı sebep olmaksızın, kiralananı üç yıl geçmedikçe eski kiracısından başkasına kiralayamaz.
        (TBK Madde 355)""",
        
        """KONU: İnternet İptali, Taahhüt Cezası, Cayma Bedeli, Abonelik Feshi.
        İÇERİK: Abonelik sözleşmelerinde tüketici, taahhüt süresi dolmadan haklı bir sebeple veya hizmet ayıplıysa ceza ödemeden sözleşmeyi feshedebilir.
        (Tüketici Kanunu)"""
    ]
    
    ids = ["gurultu", "kira_artis", "tahliye", "internet"]
    metadatas = [{"kategori": "komsu"}, {"kategori": "kira"}, {"kategori": "tahliye"}, {"kategori": "tuketici"}]

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    return collection

# --- 6. RETRIEVAL (ARAMA) ---
def kanun_maddesi_bul(collection, sorgu):
    results = collection.query(
        query_texts=[sorgu],
        n_results=1
    )
    return results['documents'][0][0]

# --- 7. ARAYÜZ ---
st.title("⚖️ Arzuhal.ai | RAG Sistemi")
st.caption("Veritabanı Taramalı Akıllı Sistem")

# Sidebar - API Key
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Key", type="password")

# --- VERİTABANINI ÇAĞIR (Artık Session State değil, Cache kullanıyoruz) ---
db_collection = get_hukuk_sistemi()

# --- FORM ---
col1, col2 = st.columns(2)
with col1:
    ad = st.text_input("Adınız Soyadınız", "Ahmet Yılmaz")
    adres = st.text_area("Adres", "Beşiktaş/İstanbul", height=70)
with col2:
    karsi_taraf = st.text_input("Muhatap", "Mehmet Demir")
    tarih = st.text_input("Tarih", "01.05.2023")

hikaye = st.text_area("Sorunu Anlatın", placeholder="Örn: Ev sahibim %100 zam istiyor.")

# --- AKSİYON ---
if st.button("🔍 Kanunu Bul ve Dilekçeyi Yaz"):
    if not api_key or not hikaye:
        st.error("Lütfen tüm alanları doldurun.")
    else:
        status_box = st.empty()
        
        # 1. RETRIEVAL
        status_box.info("💾 Veritabanında kanun maddesi taranıyor...")
        bulunan_kanun = kanun_maddesi_bul(db_collection, hikaye)
        
        st.success(f"✅ Tespit Edilen Hukuki Dayanak:\n{bulunan_kanun}")
        
        # 2. GENERATION
        status_box.info("🤖 Dilekçe yazılıyor...")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        full_prompt = f"""
        GÖREV: Aşağıdaki "BULUNAN KANUN MADDESİ"ni temel alarak resmi bir İHTARNAME hazırla.
        ROLLER: Sen "{ad}" isimli vatandaşsın.
        
        CONTEXT (BİLGİ BANKASI):
        Sistem veritabanından şu kanun maddesini buldu: "{bulunan_kanun}"
        Lütfen dilekçeyi yazarken ÖZELLİKLE bu maddeye atıf yap.
        
        KULLANICI SORUNU: {hikaye}
        
        FORMAT:
        - İHTAR EDEN: {ad}, {adres}
        - MUHATAP: {karsi_taraf}
        - KONU, AÇIKLAMALAR, HUKUKİ SEBEPLER, SONUÇ.
        - Asla markdown (**bold**) kullanma.
        """
        
        response = model.generate_content(full_prompt)
        # Temizlik
        dilekce_metni = response.text.replace("**", "").replace("##", "")
        
        status_box.empty()
        
        col_res1, col_res2 = st.columns([3,1])
        with col_res1:
            st.text_area("Sonuç", value=dilekce_metni, height=400)
        with col_res2:
            pdf_data = create_pdf(dilekce_metni)
            st.download_button("📄 PDF İNDİR", pdf_data, "dilekce.pdf", "application/pdf")