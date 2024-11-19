from operator import iconcat

import streamlit as st
import os
import logging
import pandas as pd
from pyarrow.lib import ordered_dict
from pymongo import MongoClient

TABLE_HEADERS = ["Organização", "Marca", "Type", "Taxa Mínima (R$)", "Taxa Máxima (R$)", "Indexador Referencial",
                 "Garantias Requeridas", "Person Type", "Termos e Condições"]

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("og-analytics")

# MongoDB Atlas connection configuration
MONGO_URI = os.getenv("MONGO_URI", None)
DATABASE_NAME = os.getenv("DATABASE_NAME")
ENVIRONMENT = os.getenv("ENVIRONMENT", "sandbox")

# Endpoint to fetch loans data
LOANS_COLLECTION = f"{ENVIRONMENT}.loans.rates"

# MongoDB connection
logger.debug("Connecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
logger.debug("Connected to MongoDB Atlas")

current_directory = os.path.dirname(os.path.realpath(__file__))
log_path = os.path.join(current_directory, "OpenGoLogo.png")
# Streamlit UI setup
st.set_page_config(page_title="Comparador de empréstimo bancário", layout="wide")
st.sidebar.image(log_path, use_column_width=True)
st.header("Comparação de taxas de empréstimo")

@st.dialog(title="Como usar a aplicação?", width="large")
def show_help_dialog():
    st.markdown(
        """
        <div style="font-size: 12px; color: #555;">
            <p>Esta aplicação permite comparar taxas de empréstimos de diferentes instituições financeiras participantes do Open Finance Brasil. Utilize os filtros na barra lateral para refinar sua pesquisa:</p>
            <ul>
                <li><strong>Tipo pessoa</strong>: Selecione se deseja ver empréstimos para Pessoa Física ou Pessoa Jurídica.</li>
                <li><strong>Instituição</strong>: Escolha uma ou mais instituições financeiras específicas para comparar as taxas.</li>
                <li><strong>Tipo empréstimo</strong>: Filtre pelo tipo específico de empréstimo oferecido, como crédito pessoal ou consignado.</li>
                <li><strong>Mostrar todas as instituições</strong>: Marque esta opção para visualizar todas as instituições disponíveis na tabela.</li>
            </ul>
            <p>Os resultados são apresentados na tabela abaixo. Para entender os campos da tabela, veja a sessão "Ajuda" no menu ao lado.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("O que quer dizer cada campo?"):
        st.markdown(
            """
            <div style="font-size: 12px; color: #555;">                
                <ul>
                    <li><strong>Instituição</strong>: Nome da instituição financeira participante do Open Finance que oferece o produto.</li>
                    <li><strong>Marca</strong>: Nome da marca da instituição financeira.</li>
                    <li><strong>CNPJ</strong>: Número do CNPJ da instituição.</li>
                    <li><strong>Nome do Serviço</strong>: Nomes das Tarifas cobradas sobre Serviços relacionados à Modalidade informada do Empréstimo para pessoa física/jurídica.</li>
                    <li><strong>Informação de Cobrança</strong>: Fatores geradores de cobrança que incidem sobre as Modalidades informada de Empréstimos para pessoa física/jurídica.</li>
                    <li><strong>Valor Mínimo (BRL)</strong>: Valor mínimo apurado para a tarifa de serviços sobre a base de clientes no mês de referência.<br><em>Observação:</em> Para efeito de comparação de taxas dos produtos, as instituições participantes, quando não cobram tarifas, devem enviar o valor 0.00 sinalizando que para aquela taxa não há cobrança.</li>
                    <li><strong>Valor Máximo (BRL)</strong>: Valor máximo apurado para a tarifa de serviços sobre a base de clientes no mês de referência.<br><em>Observação:</em> Para efeito de comparação de taxas dos produtos, as instituições participantes, quando não cobram tarifas, devem enviar o valor 0.00 sinalizando que para aquela taxa não há cobrança pelo serviço.</li>
                    <li><strong>Intervalo</strong>: Segundo Normativa nº 32, BCB, de 2020: Distribuição de frequência relativa dos valores de tarifas cobradas dos clientes, de que trata o § 2º do art. 3º da Circular nº 4.015, de 2020, deve dar-se com base em quatro faixas de igual tamanho, com explicitação dos valores sobre a mediana em cada uma dessas faixas. Informando: 1ª faixa, 2ª faixa, 3ª faixa e 4ª faixa.</li>
                    <li><strong>Valor (BRL)</strong>: Valor da mediana de cada faixa relativa ao serviço ofertado, informado no período, conforme Res nº 32 BCB, 2020. Exemplo: '45.00' (representa um valor monetário; por exemplo: 1547368.92, que significa R$ 1.547.368,92, considerando a moeda BRL, com o único separador sendo o '.' para indicar a casa decimal e sem separador de milhar).<br><em>Observação:</em> Para efeito de comparação de taxas dos produtos, as instituições participantes, quando não cobram tarifas, devem enviar o valor 0.00 sinalizando que para aquela taxa não há cobrança pelo serviço.</li>
                    <li><strong>Taxa</strong>: Percentual de clientes em cada faixa.</li>
                    <li><strong>Termos e Condições</strong>: Link para os termos e condições do empréstimo.</li>
                    <li><strong>Tipo de Pessoa</strong>: Indica se o empréstimo é para pessoa física ou jurídica.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )


try:
    logger.debug("Fetching loans data from MongoDB...")
    logger.debug(f"Collection name: {LOANS_COLLECTION}")
    loans_data = db[LOANS_COLLECTION].find()
    loans_data_count = db[LOANS_COLLECTION].count_documents({})
    logger.debug(f"Number of documents in collection: {loans_data_count}")
    all_fees_data = []

    if loans_data_count == 0:
        logger.warning("No documents found in loans collection.")
    for data in (loans_data or []):
        logger.debug(f"Processing data for organisation: {data.get('organisationName')}")
        organisation_name = data.get("organisationName")
        api_family_type = data.get("ApiFamilyType")
        person_type = "Pessoa Física" if api_family_type == "opendata-loans_personal-loans" else "Pessoa Jurídica"
        loan_data = data.get("loans", {}).get("data", [])

        logger.debug(f"person_type: {person_type}")

        for loan in (loan_data or []):
            participant_info = loan.get("participant", {})
            logger.debug(f"Processing loan data for participant: {participant_info.get('brand')}")
            fees = loan.get("fees", {}).get("services", [])
            for interestedRate in loan.get('interestRates', {}):
                logger.debug(f"minimumRate {interestedRate.get('minimumRate', "Não informado")}")
                all_fees_data.append(
                    {
                        "Taxa Mínima (R$)":
                            f"{float(interestedRate.get('minimumRate', "Não informado")) * 100:.2f}%".replace(',',
                                                                                                              'X').replace(
                                '.', ',').replace('X', '.'),

                        "Taxa Máxima (R$)": f"{float(interestedRate.get('maximumRate', "Não informado")) * 100:.2f}%".replace(
                            ',',
                            'X').replace(
                            '.', ',').replace('X', '.'),
                        "Indexador Referencial": interestedRate.get("referentialRateIndexer").replace('_',
                                                                                                      ' ').title(),
                        "Organização": organisation_name,
                        "Marca": participant_info.get("brand"),
                        "Garantias Requeridas": loan.get("requiredWarranties"),
                        "Termos e Condições": loan.get("termsConditions"),
                        "Person Type": person_type,
                        "Type": loan.get("type").replace('_', ' ').title()

                    }
                )

    if all_fees_data:
        # Convert to DataFrame
        fees_df = pd.DataFrame(all_fees_data)[
            TABLE_HEADERS]

        # Sidebar filters
        st.sidebar.header("Opções")


        def reset_show_all():
            st.session_state['show_all'] = False


        person_type_filter = st.sidebar.selectbox("Tipo pessoa", options=fees_df["Person Type"].unique(),
                                                  on_change=reset_show_all)

        institution_options = fees_df[fees_df["Person Type"] == person_type_filter]["Marca"].unique()

        institution_filter = st.sidebar.multiselect("Instituição",
                                                    options=[option for option in institution_options if option],
                                                    default=institution_options[:2] if len(institution_options)>2 else [
                                                        0],
                                                    on_change=reset_show_all)
        loan_type_options = \
            fees_df[(fees_df["Person Type"] == person_type_filter) & (fees_df["Marca"].isin(institution_filter))][
                "Type"].unique()

        loan_type_filter = st.sidebar.multiselect("Tipo empréstimo",
                                                  options=[option for option in loan_type_options if option],
                                                  default=loan_type_options[:1] if len(loan_type_options)>2 else [],
                                                  on_change=reset_show_all)

        # Apply filters to DataFrame
        filtered_fees_df = fees_df[
            (fees_df["Person Type"] == person_type_filter) &
            (fees_df["Marca"].isin(institution_filter)) &
            (fees_df["Type"].isin(loan_type_filter))
        ]

        logger.info(f"institution_filter {institution_filter}")
        logger.info(f"loan_type_filter {loan_type_filter}")
        logger.info(f"filtered_fees_df {filtered_fees_df.to_string()}")

        # Option to show all items
        show_all = st.sidebar.checkbox("Mostrar todas as instituições", key="show_all")

        if show_all:
            filtered_fees_df = fees_df

        # Display filtered DataFrame
        st.dataframe(filtered_fees_df.sort_values(by="Type"), use_container_width=True)

        st.markdown(
            "Os dados dessa aplicação são provenientes das próprias instituições financeiras e são obtidos através do [Open Finance Brasil](https://openfinancebrasil.org.br/).")
        st.image("https://openfinancebrasil.org.br/wp-content/themes/openbank/assets/img/logo.png",
                 use_column_width=False, width=150)

        st.sidebar.header("Ajuda")

        if st.sidebar.button("Como usar a aplicação"):
            show_help_dialog()

    else:
        logger.warning("No data available for loans.")
        st.write("No data available for loans.")

    st.sidebar.markdown("---")  # Linha horizontal para separar visualmente
    st.sidebar.markdown(
        """
        <div style="text-align: center; font-size: 12px;">
            Desenvolvido por: <a href="https://github.com/alexpereiramaranhao" target="_blank">Alex Pereira Maranhão</a>
        </div>
        """,
        unsafe_allow_html=True
    )

except Exception as e:
    logger.error(f"Error fetching loans analytics: {e}")
    st.error(f"Unable to fetch loans data. {e}")

