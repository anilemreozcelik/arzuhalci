import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Dilekçe Asistanı (V2)", page_icon="⚖️")

# --- PDF OLUŞTURMA SINIFI ---
class PDF(FPDF):
    def header(self):
        font_path = "DejaVuSans.ttf"
        try:
            if os.path.exists(font_path):
                self.add_font('DejaVu', '', font_path, uni=True)
                self.set_font('DejaVu', '', 10)
            else:
                self.set_font('Arial', '', 10)
        except:
            self.set_font('Arial', '', 10)
            
        self.cell(0, 10, 'Hukuki İhtarname Taslağı', 0, 1, 'R') # Başlığı değiştirdik
        self.ln(10)

def create_pdf(metin):
    pdf = PDF()
    pdf.add_page()
    
    font_path = "DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdf.add_font('DejaVu', '', font_path, uni=True)
        pdf.set_font('DejaVu', '', 11)
    else:
        pdf.set_font("Arial", size=11)

    pdf.multi_cell(0, 7, metin) # Satır aralığını biraz daralttık (7)
    return pdf.output(dest='S').encode('latin-1')

# --- SIDEBAR (AYARLAR) ---
st.sidebar.header("🔑 Ayarlar")

# Önce gizli anahtarı (Secrets) kontrol et
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.sidebar.success("✅ API Anahtarı Sistemde Tanımlı")
else:
    # Yoksa kullanıcıdan iste
    api_key = st.sidebar.text_input("Google Gemini API Key", type="password", placeholder="AIzaSy...")
    
st.sidebar.markdown("---")
st.sidebar.header("📌 Kişisel Bilgiler")
kullanici_ad = st.sidebar.text_input("Adınız Soyadınız", "Ahmet Yılmaz")
ev_sahibi_ad = st.sidebar.text_input("Muhatap (Ev Sahibi)", "Mehmet Demir")
adres = st.sidebar.text_area("Adresiniz", "Papatya Sok. No:5 Beşiktaş/İstanbul")
# Tarihi text olarak alalım ki format bozulmasın
tarih_bilgisi = st.sidebar.text_input("Sözleşme Tarihi", "01.05.2023") 

# --- ANA EKRAN ---
st.title("⚖️ Akıllı Dilekçe Asistanı")
st.caption("Altyapı: Gemini 2.0 Flash - Vatandaş Modu")

kullanici_hikayesi = st.text_area(
    "Sorunu detaylıca anlatın:",
    height=150,
    placeholder="Örn: Ev sahibim kirayı 5 binden 15 bine çıkarmak istiyor, kabul etmezsem çık dedi. Yasal sınırın üzerinde..."
)

# --- GEMINI FONKSİYONU (YENİLENMİŞ PROMPT) ---
def gemini_dilekce_yaz(api_key, hikaye, ad, karsi_taraf, adres, tarih):
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    
    # --- İŞTE SİHİR BURADA: DAHA KESKİN KOMUTLAR ---
    full_prompt = f"""
    GÖREV: Aşağıdaki verilere dayanarak, bir kiracının ev sahibine göndereceği resmi bir İHTARNAME hazırla.
    
    ROLLER:
    - Sen bir avukat DEĞİLSİN. Sen "{ad}" isimli vatandaşsın.
    - Metni 1. tekil şahıs (Ben diliyle) yaz. (Örn: "Müvekkilim" deme, "Tarafımla imzalanan" de).
    - İmza kısmına SADECE "{ad}" yaz. Asla "Avukat" unvanı kullanma.
    
    KURALLAR:
    1. Boşluk Doldurma: Sana verilen tarih ({tarih}) ve isimleri ({ad}, {karsi_taraf}) metnin içine mutlak yerleştir. Asla "..." veya "[Tarih Girin]" gibi yer tutucu bırakma.
    2. Hukuki Dayanak: Türk Borçlar Kanunu (TBK) Madde 344 ve ilgili TÜFE sınırlamalarına atıf yap.
    3. Üslup: Ciddi, kararlı, hukuki ama sade bir dil kullan.
    4. Format: Standart İhtarname formatı (KEŞİDECİ, MUHATAP, KONU, AÇIKLAMALAR, SONUÇ).
    
    GİRİŞ VERİLERİ:
    Keşideci (Gönderen): {ad}
    Adres: {adres}
    Sözleşme Başlangıç Tarihi: {tarih}
    Muhatap: {karsi_taraf}
    Konu Özeti: {hikaye}
    """

    response = model.generate_content(full_prompt)
    # TEMİZLİK KODU (YENİ EKLENEN KISIM)
    temiz_metin = response.text
    temiz_metin = temiz_metin.replace("**", "")  # Kalın yapma yıldızlarını sil
    temiz_metin = temiz_metin.replace("##", "")  # Başlık karelerini sil
    temiz_metin = temiz_metin.replace("* ", "- ") # Madde başı yıldızlarını tireye çevir
    
    return temiz_metin

# --- BUTON ---
if st.button("🚀 Dilekçeyi Oluştur"):
    if not api_key:
        st.error("API Key eksik.")
    elif not kullanici_hikayesi:
        st.error("Hikaye eksik.")
    else:
        with st.spinner("Yapay zeka verileri işliyor..."):
            try:
                sonuc_metin = gemini_dilekce_yaz(api_key, kullanici_hikayesi, kullanici_ad, ev_sahibi_ad, adres, tarih_bilgisi)
                
                st.success("Dilekçe Hazır!")
                st.text_area("Sonuç:", value=sonuc_metin, height=600)
                
                pdf_data = create_pdf(sonuc_metin)
                st.download_button(
                    label="📄 PDF İndir",
                    data=pdf_data,
                    file_name="ihtarname.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Hata: {e}")