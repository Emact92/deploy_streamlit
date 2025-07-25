import streamlit as st
import pandas as pd
from google.cloud import firestore
from google.oauth2 import service_account
import json

# --- Inicialización de Firestore ---
# Cargar credenciales desde Streamlit secrets
try:
    key_dict = json.loads(st.secrets["textkey"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    # Inicializar cliente de Firestore con credenciales y ID del proyecto
    # Asegúrate de que "names-project-demo" sea el ID correcto de tu proyecto de Firebase
    db = firestore.Client(credentials=creds, project="names-project-demo")
    dbNames = db.collection("names")
except Exception as e:
    st.error(f"Error al inicializar Firestore. Asegúrate de que 'textkey' esté configurado correctamente en Streamlit secrets y que el ID del proyecto sea correcto: {e}")
    st.stop() # Detener la aplicación si Firestore no se puede inicializar

# --- Sección de Creación de Nuevo Registro ---
st.header("Nuevo Registro")
# Usar 'key' para asegurar la unicidad de los widgets si se re-renderizan
new_record_index = st.text_input("Index", key="new_index_input")
new_record_name = st.text_input("Nombre", key="new_name_input")
new_record_sex = st.selectbox('Seleccionar Sexo', ('F', 'M', 'Other'), key="new_sex_select")
submit_new_record = st.button("Crear Nuevo Registro")

# Una vez que se envía el nombre, subirlo a la base de datos
if submit_new_record:
    if new_record_index and new_record_name and new_record_sex:
        try:
            # Usar el nombre como el ID del documento para facilitar la búsqueda
            doc_ref = dbNames.document(new_record_name)
            doc_ref.set({
                "index": new_record_index,
                "name": new_record_name,
                "sex": new_record_sex
            })
            st.success(f"Registro '{new_record_name}' insertado correctamente.")
            st.rerun() # Volver a ejecutar para limpiar entradas y refrescar la tabla
        except Exception as e:
            st.error(f"Error al crear el registro: {e}")
    else:
        st.warning("Por favor, rellena todos los campos para el nuevo registro.")

# --- Función Auxiliar para Cargar un Documento por Nombre ---
def load_document_by_name(name_to_search):
    """Carga un documento de Firestore buscando por el campo 'name'."""
    try:
        # Consultar la colección para documentos donde el campo 'name' coincide
        # y limitar a 1 resultado ya que el nombre se usa como ID (asumiendo unicidad)
        names_query = dbNames.where('name', '==', name_to_search).limit(1)
        docs = list(names_query.stream())
        if docs:
            return docs[0] # Devolver el primer documento coincidente
        return None
    except Exception as e:
        st.error(f"Error al buscar el nombre: {e}")
        return None

# --- Barra Lateral para Búsqueda, Eliminación y Actualización ---
st.sidebar.header("Operaciones de Búsqueda y Edición")
search_name_input = st.sidebar.text_input("Buscar por Nombre", key="search_name_input")
btn_search = st.sidebar.button("Buscar Registro")

if btn_search:
    doc_found = load_document_by_name(search_name_input)
    if doc_found:
        st.sidebar.subheader(f"Detalles de '{search_name_input}':")
        st.sidebar.json(doc_found.to_dict()) # Mostrar como JSON para mayor claridad
    else:
        st.sidebar.warning(f"El nombre '{search_name_input}' no existe.")

st.sidebar.markdown("""---""")

# --- Sección de Eliminación ---
st.sidebar.subheader("Eliminar Registro")
# El botón de eliminar opera sobre el último nombre buscado
btn_delete = st.sidebar.button("Eliminar Registro Buscado")

if btn_delete:
    if search_name_input:
        doc_to_delete = load_document_by_name(search_name_input)
        if doc_to_delete:
            try:
                dbNames.document(doc_to_delete.id).delete()
                st.sidebar.success(f"'{search_name_input}' eliminado correctamente.")
                st.rerun() # Volver a ejecutar para refrescar la tabla
            except Exception as e:
                st.sidebar.error(f"Error al eliminar '{search_name_input}': {e}")
        else:
            st.sidebar.warning(f"No se encontró el registro '{search_name_input}' para eliminar.")
    else:
        st.sidebar.info("Por favor, busca un nombre primero para eliminar.")

st.sidebar.markdown("""---""")

# --- Sección de Actualización ---
st.sidebar.subheader("Actualizar Registro")
# Campo para el nombre del registro a actualizar (el ID del documento)
update_target_name = st.sidebar.text_input("Nombre del registro a actualizar (actual)", key="update_target_name_input")
# Campos para los nuevos valores de los atributos
new_update_index = st.sidebar.text_input("Nuevo Index (opcional)", key="new_update_index_input")
new_update_name = st.sidebar.text_input("Nuevo Nombre (opcional)", key="new_update_name_input")
new_update_sex = st.sidebar.selectbox('Nuevo Sexo (opcional)', ('F', 'M', 'Other', ''), index=3, key="new_update_sex_select") # Añadir opción vacía

btn_update = st.sidebar.button("Actualizar Registro")

if btn_update:
    if update_target_name:
        doc_to_update = load_document_by_name(update_target_name)
        if doc_to_update:
            update_data = {}
            # Solo añadir al diccionario de actualización si el campo no está vacío
            if new_update_index:
                update_data["index"] = new_update_index
            if new_update_sex != '': # Comprobar que no sea la opción vacía
                update_data["sex"] = new_update_sex

            # Manejar el cambio de nombre (que es el ID del documento)
            if new_update_name and new_update_name != update_target_name:
                # Si el nuevo nombre es diferente, implica cambiar el ID del documento.
                # Esto requiere crear un nuevo documento y eliminar el antiguo.
                existing_new_doc = load_document_by_name(new_update_name)
                if existing_new_doc:
                    st.sidebar.error(f"El nuevo nombre '{new_update_name}' ya existe. Por favor, elige otro.")
                else:
                    try:
                        # Obtener los datos actuales del documento para no perder campos no actualizados
                        new_doc_data = doc_to_update.to_dict()
                        new_doc_data["name"] = new_update_name # Actualizar el campo 'name'

                        # Aplicar otras actualizaciones si se proporcionaron
                        if new_update_index: new_doc_data["index"] = new_update_index
                        if new_update_sex != '': new_doc_data["sex"] = new_update_sex

                        # Crear el nuevo documento con el nuevo ID
                        dbNames.document(new_update_name).set(new_doc_data)
                        # Eliminar el documento antiguo
                        dbNames.document(doc_to_update.id).delete()
                        st.sidebar.success(f"Registro '{update_target_name}' actualizado a '{new_update_name}' correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error al actualizar el nombre del registro: {e}")
            elif update_data: # Si no se cambió el nombre (ID), solo actualizar los campos del documento existente
                try:
                    dbNames.document(doc_to_update.id).update(update_data)
                    st.sidebar.success(f"Registro '{update_target_name}' actualizado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Error al actualizar el registro: {e}")
            else:
                st.sidebar.warning("No se proporcionaron nuevos valores para actualizar.")
        else:
            st.sidebar.warning(f"El nombre '{update_target_name}' no existe para actualizar.")
    else:
        st.sidebar.info("Por favor, introduce el nombre del registro a actualizar.")

# --- Sección para Mostrar Todos los Registros ---
st.subheader("Registros Actuales")
try:
    # Obtener todos los documentos de la colección 'names'
    names_ref = list(dbNames.stream())
    if names_ref:
        # Convertir documentos a diccionarios y luego a un DataFrame de Pandas
        names_dict = [doc.to_dict() for doc in names_ref]
        names_dataframe = pd.DataFrame(names_dict)
        st.dataframe(names_dataframe)
    else:
        st.info("No hay registros en la colección 'names'.")
except Exception as e:
    st.error(f"Error al cargar los registros: {e}")
