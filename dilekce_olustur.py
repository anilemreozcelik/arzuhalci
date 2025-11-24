import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import os

# --- SAYFA VE TASARIM AYARLARI ---
st.set_page_config(
    page_title="Arzuhal.ai | Yapay Zeka Hukuk Asistanı",
    page_icon="⚖️",
    layout="centered", # Sayfayı ortalar
    initial_sidebar_state="collapsed" # Sol menüyü kapalı başlatır
)

# --- CSS İLE GÖRSEL MAKYAJ ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    /* "Made with Streamlit" yazısını gizle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Butonları özelleştir */
    .stButton>button {
        width: 100%;
        background-color: #0E1117;
        color: white;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- PDF OLUŞTURMA SINIFI (GÜNCELLENMİŞ - CİDDİ FONT) ---
class PDF(FPDF):
    def header(self):
        # Font Dosyasının Adı (GitHub'a yüklediğiniz dosya ile AYNI olmalı)
        font_path = "LiberationSerif-Regular.ttf"
        
        try:
            if os.path.exists(font_path):
                # 'Times' takma adıyla fontu ekliyoruz
                self.add_font('TimesNew', '', font_path, uni=True)
                self.set_font('TimesNew', '', 10)
            else:
                # Dosya yoksa mecburen standart Arial
                self.set_font('Arial', '', 10)
        except:
            self.set_font('Arial', '', 10)
            
        # Header boş kalsın (Antetli kağıt havası için)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        
        # Footer için de aynı font
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
    
    # 1. HAMLE: Kenar boşluklarını 20mm'den 15mm'ye düşürdük.
    # Bu bize dikeyde yaklaşık 10mm (2-3 satır) ekstra alan kazandırır.
    pdf.set_margins(15, 15, 15)
    
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    font_path = "LiberationSerif-Regular.ttf"
    if os.path.exists(font_path):
        pdf.add_font('TimesNew', '', font_path, uni=True)
        # Fontu 11'den 10.5'a çektik. Gözle fark edilmez ama yer kazandırır.
        pdf.set_font('TimesNew', '', 10.5) 
    else:
        pdf.set_font("Arial", size=10)

    # 2. HAMLE: Satır aralığını 6mm'den 5mm'ye düşürdük.
    # Metin bloğu daha kompakt durur.
    pdf.multi_cell(0, 5, metin.strip(), align='J')
    
    return pdf.output(dest='S').encode('latin-1')
    
# --- SIDEBAR (GİZLİ AYARLAR) ---
st.sidebar.title("⚙️ Ayarlar")
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ Sistem Bağlı")
else:
    api_key = st.sidebar.text_input("API Key Girin", type="password")

st.sidebar.info("Bu uygulama Gemini 2.0 Flash modeli ile çalışmaktadır.")

# --- ANA EKRAN (HEADER) ---
st.title("⚖️ Arzuhal.ai")
st.markdown("**Siz derdinizi anlatın, yapay zeka hukuki dilekçenizi yazsın.**")

# Nasıl Çalışır Kutusu (Expander)
with st.expander("ℹ️ Nasıl Çalışır? (Okumak için tıklayın)"):
    st.write("""
    1. Kişisel bilgilerinizi ve sözleşme tarihinizi girin.
    2. Sorununuzu halk diliyle, samimi bir şekilde anlatın.
    3. 'Dilekçeyi Hazırla' butonuna basın.
    4. Yapay zeka saniyeler içinde resmi PDF'inizi oluşturacak.
    """)

st.divider() # Çizgi çek

# --- FORM ALANI (SÜTUNLAR) ---
st.subheader("1. Bilgileriniz")

col1, col2 = st.columns(2) # Ekranı ikiye böl

with col1:
    kullanici_ad = st.text_input("Adınız Soyadınız", placeholder="Örn: Ahmet Yılmaz")
    adres = st.text_area("Adresiniz", placeholder="Mahalle, Sokak, İlçe/İl", height=100)

with col2:
    ev_sahibi_ad = st.text_input("Karşı Taraf (Muhatap)", placeholder="Örn: Mehmet Demir")
    tarih_bilgisi = st.text_input("Sözleşme/Olay Tarihi", placeholder="Örn: 01.05.2023")

st.subheader("2. Sorununuz Nedir?")
kullanici_hikayesi = st.text_area(
    "Detaylar",
    height=150,
    label_visibility="collapsed", # Başlığı gizle (yukarıda subheader var)
    placeholder="Örn: Ev sahibim kirayı yasal sınırın çok üzerinde artırmak istiyor. 'Kabul etmezsen evden çık' diye tehdit ediyor..."
)

# --- GEMINI FONKSİYONU ---
def gemini_dilekce_yaz(api_key, hikaye, ad, karsi_taraf, adres, tarih):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    
    full_prompt = f"""
    GÖREV: Aşağıdaki verilere dayanarak, resmi ve hukuki standartlara tam uygun bir İHTARNAME hazırla.
    
    ROLLER: Sen "{ad}" isimli vatandaşsın.
    
    KURALLAR:
    1. FORMAT: Aşağıdaki başlıkları MUTLAKA kullan:
       - İHTAR EDEN (KEŞİDECİ)
       - MUHATAP
       - KONU
       - AÇIKLAMALAR (Maddeler halinde, hukuki dille)
       - HUKUKİ SEBEPLER (Buraya şunu yaz: "TBK, HMK ve ilgili yasal mevzuat")
       - DELİLLER (Buraya şunu yaz: "Kira sözleşmesi, banka dekontları, whatsapp yazışmaları ve her türlü yasal delil")
       - SONUÇ VE İSTEM
    
    2. İÇERİK:
       - Tarih: {tarih}, İsimler: {ad}, {karsi_taraf}.
       - Türk Borçlar Kanunu Madde 344 ve TÜFE sınırına atıf yap.
       - Asla **kalın**, *italik* kullanma. Düz metin ver.
    
    VERİLER:
    Keşideci: {ad}
    Adres: {adres}
    Tarih: {tarih}
    Muhatap: {karsi_taraf}
    Olay: {hikaye}
    """
    response = model.generate_content(full_prompt)
    
    # Ekstra Temizlik (Garanti olsun)
    clean_text = response.text.replace("**", "").replace("##", "").replace("* ", "- ")
    return clean_text

# --- AKSİYON BUTONU ---
st.markdown("<br>", unsafe_allow_html=True) # Biraz boşluk

if st.button("✨ Dilekçeyi Şimdi Oluştur", type="primary"):
    if not api_key:
        st.error("API Key bulunamadı.")
    elif not kullanici_hikayesi or not kullanici_ad:
        st.warning("Lütfen adınızı ve sorununuzu eksiksiz girin.")
    else:
        with st.spinner("Yapay zeka kanun maddelerini tarıyor..."):
            try:
                sonuc_metin = gemini_dilekce_yaz(api_key, kullanici_hikayesi, kullanici_ad, ev_sahibi_ad, adres, tarih_bilgisi)
                
                st.success("Dilekçeniz Hazır!")
                
                # İki sütun: Biri metin önizleme, biri indirme butonu
                res_col1, res_col2 = st.columns([3, 1])
                
                with res_col1:
                    st.text_area("Önizleme", value=sonuc_metin, height=400)
                
                with res_col2:
                    st.info("Bu belgeyi indirip notere götürebilirsiniz.")
                    pdf_data = create_pdf(sonuc_metin)
                    st.download_button(
                        label="📄 PDF İNDİR",
                        data=pdf_data,
                        file_name="Arzuhal_AI_Dilekce.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"Hata: {e}")