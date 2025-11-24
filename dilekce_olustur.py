import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import chromadb
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Arzuhal.ai | RAG Destekli", page_icon="⚖️")

# --- PDF SINIFI (AYNI) ---
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

# --- RAG SİSTEMİ (VECTOR DATABASE) ---
# Gerçek hayatta burası mevzuat.gov.tr'den çekilen binlerce veri olur.
# Biz MVP için en kritik maddeleri elle ekliyoruz.
def veritabani_hazirla():
    chroma_client = chromadb.Client()
    
    # Koleksiyon oluştur (Eğer varsa silip tekrar kuruyoruz - MVP için)
    try:
        chroma_client.delete_collection(name="hukuk_kutuphanesi")
    except:
        pass
    
    collection = chroma_client.create_collection(name="hukuk_kutuphanesi")

    # BELGELER (Knowledge Base)
    documents = [
        "Kiracı, kiralananı özenle kullanmak ve komşulara saygı göstermekle yükümlüdür. Gürültü yapmak tahliye sebebidir.",
        "Konut ve çatılı işyeri kiralarında kira bedeli artışı, bir önceki kira yılındaki TÜFE (On iki aylık ortalama) oranını geçemez. (TBK Madde 344)",
        "Kat malikleri, gerek bağımsız bölümlerini gerekse ortak yerleri kullanırken doğruluk kaidelerine uymak, özellikle birbirini rahatsız etmemek, birbirinin haklarını çiğnememek ve yönetim planı hükümlerine uymakla karşılıklı olarak yükümlüdürler. (Kat Mülkiyeti Kanunu Madde 18 - Gürültü Yasağı)",
        "Kiraya veren, gereksinim amacıyla kiralananın boşaltılmasını sağladığında, haklı sebep olmaksızın, kiralananı üç yıl geçmedikçe eski kiracısından başkasına kiralayamaz. (TBK Madde 355)",
        "İnternet abonelik sözleşmelerinde tüketici, taahhüt süresi dolmadan haklı bir sebeple sözleşmeyi feshedebilir. (Tüketici Kanunu)"
    ]
    
    # ID'ler ve Metadata
    ids = ["tbk_komsu", "tbk_344_kira_artis", "kmk_18_gurultu", "tbk_355_yeniden_kiralama", "tkh_internet"]
    metadatas = [{"kanun": "TBK"}, {"kanun": "TBK"}, {"kanun": "KMK"}, {"kanun": "TBK"}, {"kanun": "TKH"}]

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    return collection

# --- RETRIEVAL FONKSİYONU ---
def kanun_maddesi_bul(collection, sorgu):
    # Kullanıcının sorusuna en yakın 1 kanun maddesini bul
    results = collection.query(
        query_texts=[sorgu],
        n_results=1 
    )
    # Bulunan en alakalı kanun metnini döndür
    return results['documents'][0][0]

# --- ARAYÜZ ---
st.title("⚖️ Arzuhal.ai | RAG Sistemi")
st.caption("Veritabanı Taramalı Akıllı Sistem")

# Sidebar
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Key", type="password")

# Veritabanını başlat (Session state ile sadece 1 kere çalışmasını sağla)
if 'db_collection' not in st.session_state:
    st.session_state.db_collection = veritabani_hazirla()

# --- FORM ---
col1, col2 = st.columns(2)
with col1:
    ad = st.text_input("Adınız Soyadınız", "Ahmet Yılmaz")
    adres = st.text_area("Adres", "Beşiktaş/İstanbul", height=70)
with col2:
    karsi_taraf = st.text_input("Muhatap", "Mehmet Demir")
    tarih = st.text_input("Tarih", "01.05.2023")

hikaye = st.text_area("Sorunu Anlatın", placeholder="Örn: Komşum gece yarısı matkap çalıştırıyor, uyuyamıyoruz.")

# --- RAG + GENERATION ---
if st.button("🔍 Kanunu Bul ve Dilekçeyi Yaz"):
    if not api_key or not hikaye:
        st.error("Eksik bilgi.")
    else:
        status_box = st.empty() # Durum çubuğu
        
        # 1. ADIM: RETRIEVAL (Bilgi Getirme)
        status_box.info("💾 Veritabanında ilgili kanun maddesi taranıyor...")
        
        # ChromaDB ile arama yap
        bulunan_kanun = kanun_maddesi_bul(st.session_state.db_collection, hikaye)
        
        st.success(f"✅ Bulunan İlgili Kanun: {bulunan_kanun}")
        
        # 2. ADIM: GENERATION (Üretim)
        status_box.info("🤖 Dilekçe yazılıyor...")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        # Prompt'a bulduğumuz kanunu "Context" olarak veriyoruz
        full_prompt = f"""
        GÖREV: Aşağıdaki "BULUNAN KANUN MADDESİ"ni temel alarak resmi bir İHTARNAME hazırla.
        
        ROLLER: Sen "{ad}" isimli vatandaşsın.
        
        CONTEXT (BİLGİ BANKASI):
        Sistem veritabanından şu kanun maddesini buldu: "{bulunan_kanun}"
        Lütfen dilekçeyi yazarken ÖZELLİKLE bu maddeye atıf yap ve içeriği buna dayandır.
        
        KULLANICI SORUNU: {hikaye}
        
        FORMAT:
        - İHTAR EDEN: {ad}, {adres}
        - MUHATAP: {karsi_taraf}
        - KONU, AÇIKLAMALAR, HUKUKİ SEBEPLER, SONUÇ.
        - Asla markdown (**bold**) kullanma.
        """
        
        response = model.generate_content(full_prompt)
        dilekce_metni = response.text.replace("**", "").replace("##", "")
        
        status_box.empty() # Mesajı temizle
        
        col_res1, col_res2 = st.columns([3,1])
        with col_res1:
            st.text_area("Sonuç", value=dilekce_metni, height=400)
        with col_res2:
            pdf_data = create_pdf(dilekce_metni)
            st.download_button("İNDİR", pdf_data, "dilekce.pdf", "application/pdf")