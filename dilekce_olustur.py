# --- 1. YAMA: SQLITE FIX (STREAMLIT CLOUD İÇİN) ---
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
st.set_page_config(page_title="Arzuhal.ai | Pro", page_icon="⚖️")

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

# --- 5. RAG SİSTEMİ (AKILLI DATABASE) ---
@st.cache_resource
def get_hukuk_sistemi():
    chroma_client = chromadb.Client()
    try:
        chroma_client.delete_collection(name="hukuk_kutuphanesi_v2")
    except:
        pass
    
    collection = chroma_client.create_collection(name="hukuk_kutuphanesi_v2")

    # BELGELERİ GÜÇLENDİRDİK (Yüksek ses, matkap vs. ekledik)
    documents = [
        """KONU: Gürültü, Komşu, Rahatsızlık, Yüksek Ses, Matkap, Müzik, Bağrışma, Köpek Sesi. 
        İÇERİK: KMK Madde 18 gereği kat malikleri birbirini rahatsız etmemek ve gürültü yapmamakla yükümlüdür. Sürekli gürültü (yüksek ses, müzik vb.) tahliye sebebidir. 
        (Kat Mülkiyeti Kanunu Madde 18)""",
        
        """KONU: Kira Zammı, Kira Artışı, Fahiş Fiyat, Yüksek Zam, Enflasyon, %25 Sınırı.
        İÇERİK: TBK Madde 344 gereği kira artışı, bir önceki kira yılındaki TÜFE (12 aylık ortalama) oranını geçemez. Ev sahibi keyfi yüksek zam yapamaz.
        (Türk Borçlar Kanunu Madde 344)""",
        
        """KONU: Evden Çıkarma, Tahliye Taahhütnamesi, Ev Sahibi Çık Diyor, Oğlum Gelecek, İhtiyaç Nedeniyle Tahliye.
        İÇERİK: Kiraya veren, kendisi veya yakını oturacaksa (gereksinim) tahliye isteyebilir. Ancak haklı sebep yoksa keyfi çıkaramaz.
        (TBK Madde 350/355)""",
        
        """KONU: İnternet İptali, Taahhüt Cezası, Cayma Bedeli, Abonelik Feshi.
        İÇERİK: Tüketici Kanunu gereği, taahhütlü aboneliklerde hizmet ayıplıysa veya 1 yıldan uzun sözleşmelerde cezasız fesih hakkı vardır.
        (Tüketici Hakları Kanunu)"""
    ]
    
    ids = ["gurultu_1", "kira_1", "tahliye_1", "internet_1"]
    metadatas = [{"kat": "gurultu"}, {"kat": "kira"}, {"kat": "tahliye"}, {"kat": "tuketici"}]

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    return collection

# --- 6. YENİ ARAMA STRATEJİSİ (TOP 3 + LLM KARARI) ---
def kanun_maddesi_bul_ve_hazirla(collection, sorgu):
    # ARTIK TEK BİR SONUÇ DEĞİL, EN İYİ 3 SONUCU GETİRİYORUZ
    results = collection.query(
        query_texts=[sorgu],
        n_results=3  # Şansımızı artırdık
    )
    
    # 3 maddeyi alt alta birleştirip tek metin yapıyoruz
    bulunanlar = ""
    for i, doc in enumerate(results['documents'][0]):
        bulunanlar += f"SEÇENEK {i+1}: {doc}\n\n"
        
    return bulunanlar

# --- 7. ARAYÜZ ---
st.title("⚖️ Arzuhal.ai | Akıllı RAG")
st.caption("Çoklu Tarama & Akıllı Seçim Modülü")

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("API Key", type="password")

db_collection = get_hukuk_sistemi()

col1, col2 = st.columns(2)
with col1:
    ad = st.text_input("Adınız Soyadınız", "Ahmet Yılmaz")
    adres = st.text_area("Adres", "Beşiktaş/İstanbul", height=70)
with col2:
    karsi_taraf = st.text_input("Muhatap", "Mehmet Demir")
    tarih = st.text_input("Tarih", "01.05.2023")

hikaye = st.text_area("Sorunu Anlatın", placeholder="Örn: Komşum çok yüksek ses yapıyor.")

if st.button("🔍 Analiz Et ve Yaz"):
    if not api_key or not hikaye:
        st.error("Lütfen alanları doldurun.")
    else:
        status = st.empty()
        
        # 1. RETRIEVAL (Geniş Arama)
        status.info("💾 Veritabanında olası kanunlar taranıyor...")
        
        # Buradan artık 3 tane potansiyel kanun dönüyor
        olasi_kanunlar = kanun_maddesi_bul_ve_hazirla(db_collection, hikaye)
        
        # Kullanıcıya ne bulduğumuzu gösterelim (debug için iyi olur)
        with st.expander("Sistemin Bulduğu Olası Kanun Maddeleri (Tıklayıp Görün)"):
            st.text(olasi_kanunlar)
        
        # 2. GENERATION (Akıllı Seçim)
        status.info("🤖 Yapay zeka en uygun kanunu seçiyor ve dilekçeyi yazıyor...")
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        
        # PROMPT DEĞİŞTİ: Artık "Seçim Yap" diyoruz
        full_prompt = f"""
        GÖREV: Aşağıdaki "BULUNAN KANUN MADDELERİ" listesinden, kullanıcının sorununa EN UYGUN olanı seç ve ona göre resmi bir İHTARNAME hazırla.
        
        KULLANICI SORUNU: {hikaye}
        
        BULUNAN KANUN MADDELERİ (Bunlardan en alakalı olanı kullan):
        {olasi_kanunlar}
        
        ROLLER: Sen "{ad}" isimli vatandaşsın.
        
        KURALLAR:
        1. Sadece seçtiğin doğru kanun maddesine atıf yap. Diğerlerini görmezden gel.
        2. Eğer konu gürültü ise "Kat Mülkiyeti Kanunu", kira ise "TBK 344" kullan. Yanlış kanunu seçme.
        3. Format: İHTAR EDEN, MUHATAP, KONU, AÇIKLAMALAR, HUKUKİ SEBEPLER, SONUÇ.
        4. Asla markdown (**bold**) kullanma.
        
        VERİLER:
        Keşideci: {ad}, Adres: {adres}
        Muhatap: {karsi_taraf}
        Tarih: {tarih}
        """
        
        response = model.generate_content(full_prompt)
        dilekce_metni = response.text.replace("**", "").replace("##", "")
        
        status.empty()
        st.success("✅ Dilekçe Oluşturuldu")
        
        col_res1, col_res2 = st.columns([3,1])
        with col_res1:
            st.text_area("Sonuç", value=dilekce_metni, height=400)
        with col_res2:
            pdf_data = create_pdf(dilekce_metni)
            st.download_button("📄 PDF İNDİR", pdf_data, "dilekce.pdf", "application/pdf")