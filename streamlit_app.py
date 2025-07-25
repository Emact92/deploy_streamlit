import streamlit as st
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
import json

# Cargar las credenciales desde el archivo secrets.toml
key_dict = json.loads(st.secrets["textkey"])
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds, project="names-firebase")
dbNames = db.collection("names")

# 📝 Sección principal para registrar nuevos nombres
st.header("Nuevo registro")
index = st.text_input("Index")
name = st.text_input("Name")
sex = st.selectbox("Select Sex", ("F", "M", "Other"))
submit = st.button("Crear nuevo registro")

if index and name and sex and submit:
    doc_ref = db.collection("names").document(name)
    doc_ref.set({
        "index": index,
        "name": name,
        "sex": sex
    })
    st.sidebar.write("✅ Registro insertado correctamente")

# 🔍 Función para cargar documentos por nombre
def loadByName(name):
    names_ref = dbNames.where("name", "==", name)
    for doc in names_ref.stream():
        return doc
    return None

# 📘 Sección para búsqueda de registros
st.sidebar.subheader("Buscar nombre")
nameSearch = st.sidebar.text_input("nombre")
btnFiltrar = st.sidebar.button("Buscar")

if btnFiltrar:
    doc = loadByName(nameSearch)
    if doc is None:
        st.sidebar.write("❌ Nombre no existe")
    else:
        st.sidebar.write(doc.to_dict())

st.sidebar.markdown("---")

# 🗑️ Sección para eliminar registros
btnEliminar = st.sidebar.button("Eliminar")
if btnEliminar:
    deletename = loadByName(nameSearch)
    if deletename is None:
        st.sidebar.write(f"❌ {nameSearch} no existe")
    else:
        dbNames.document(deletename.id).delete()
        st.sidebar.write(f"🗑️ {nameSearch} eliminado")

st.sidebar.markdown("---")

# 🔄 Sección para actualizar registros
newname = st.sidebar.text_input("Actualizar nombre")
btnActualizar = st.sidebar.button("Actualizar")

if btnActualizar:
    updatename = loadByName(nameSearch)
    if updatename is None:
        st.sidebar.write(f"❌ {nameSearch} no existe")
    else:
        dbNames.document(updatename.id).update({"name": newname})
        st.sidebar.write(f"✅ {nameSearch} actualizado a {newname}")

# 📊 Mostrar todos los registros en tabla
names_ref = list(db.collection("names").stream())
names_dict = [doc.to_dict() for doc in names_ref]
names_dataframe = pd.DataFrame(names_dict)
st.dataframe(names_dataframe)
