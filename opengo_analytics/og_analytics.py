import streamlit as st
import os
import logging
import pandas as pd
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
logger.info("Connecting to MongoDB...")
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
logger.info("Connected to MongoDB Atlas")

# Streamlit UI setup
st.set_page_config(page_title="Comparador de empréstimo bancário", layout="wide")
st.sidebar.image("OpenGoLogo.png", use_column_width=True)
st.header("Comparação de taxas de empréstimo")

try:
    logger.info("Fetching loans data from MongoDB...")
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

        logger.info(f"person_type: {person_type}")

        for loan in (loan_data or []):
            participant_info = loan.get("participant", {})
            logger.debug(f"Processing loan data for participant: {participant_info.get('brand')}")
            fees = loan.get("fees", {}).get("services", [])
            for interestedRate in loan.get('interestRates', {}):
                logger.info(f"minimumRate {interestedRate.get('minimumRate', "Não informado")}")
                all_fees_data.append(
                    {
                        "Taxa Mínima (R$)":
                            f"{float(interestedRate.get('minimumRate', "Não informado"))*100:.2f}%".replace(',',
                                                                                                        'X').replace(
                                '.', ',').replace('X', '.'),

                        "Taxa Máxima (R$)": f"{float(interestedRate.get('maximumRate', "Não informado"))*100:.2f}%".replace(',',
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
        institution_filter = st.sidebar.selectbox("Instituição",
                                                  options=[option for option in institution_options if option],
                                                  on_change=reset_show_all)
        loan_type_options = \
            fees_df[(fees_df["Person Type"] == person_type_filter) & (fees_df["Marca"] == institution_filter)][
                "Type"].unique()
        loan_type_filter = st.sidebar.selectbox("Tipo empréstimo",
                                                options=[option for option in loan_type_options if option],
                                                on_change=reset_show_all)

        # Apply filters to DataFrame
        filtered_fees_df = fees_df[
            (fees_df["Person Type"] == person_type_filter) &
            (fees_df["Marca"] == institution_filter) &
            (fees_df["Type"] == loan_type_filter)
            ]

        # Option to show all items
        show_all = st.sidebar.checkbox("Mostrar todas as instituições", key="show_all")

        if show_all:
            filtered_fees_df = fees_df

        # Group data by Organização and Service Name to remove duplicates
        logger.info("Grouping fees data by Organisation and Service Name to remove duplicates...")
        grouped_fees_df = filtered_fees_df.groupby(['Organização', 'Marca'], as_index=False).first()

        # Display filtered DataFrame
        st.dataframe(grouped_fees_df, use_container_width=True,
                     height=int(len(grouped_fees_df) * 35) if len(grouped_fees_df) < 20 else 700)

        st.markdown(
            "Os dados dessa aplicação são provenientes das próprias instituições financeiras e são obtidos através do [Open Finance Brasil](https://openfinancebrasil.org.br/).")
        st.image("https://openfinancebrasil.org.br/wp-content/themes/openbank/assets/img/logo.png",
                 use_column_width=False, width=150)

        st.sidebar.header("Ajuda")
        with st.sidebar.expander("Explicação dos campos da tabela"):
            st.markdown(
                """
                - **Instituição**: Nome da instituição financeira participante do Open Finance que oferece o produto.
                - **Marca**: Nome da marca da instituição financeira.
                - **CNPJ**: Número do CNPJ da instituição.
                - **Nome do Serviço**: Nomes das Tarifas cobradas sobre Serviços relacionados à Modalidade informada do Empréstimo para pessoa física/jurídica.
                - **Informação de Cobrança**: Fatores geradores de cobrança que incidem sobre as Modalidades informada de Empréstimos para pessoa física/jurídica.
                - **Valor Mínimo (BRL)**: Valor mínimo apurado para a tarifa de serviços sobre a base de clientes no mês de referência

                    Observação: Para efeito de comparação de taxas dos produtos, as instituições participantes, quando não cobram tarifas, devem enviar o valor 0.00 sinalizando que para aquela taxa não há cobrança
                - **Valor Máximo (BRL)**: Valor máximo apurado para a tarifa de serviços sobre a base de clientes no mês de referência

                    Observação: Para efeito de comparação de taxas dos produtos, as instituições participantes, quando não cobram tarifas, devem enviar o valor 0.00 sinalizando que para aquela taxa não há cobrança pelo serviço.
                - **Intervalo**: Segundo Normativa nº 32, BCB, de 2020: Distribuição de frequência relativa dos valores de tarifas cobradas dos clientes, de que trata o § 2º do art. 3º da Circular nº 4.015, de 2020, deve dar-se com base em quatro faixas de igual tamanho, com explicitação dos valores sobre a mediana em cada uma dessas faixas. Informando: 1ª faixa, 2ª faixa, 3ª faixa e 4ª faixa
                - **Valor (BRL)**: Valor da mediana de cada faixa relativa ao serviço ofertado, informado no período, conforme Res nº 32 BCB, 2020. p.ex. '45.00' (representa um valor monetário. p.ex: 1547368.92. Este valor, considerando que a moeda seja BRL, significa R$ 1.547.368,92. O único separador presente deve ser o '.' (ponto) para indicar a casa decimal. Não deve haver separador de milhar).

                    Observação: Para efeito de comparação de taxas dos produtos, as instituições participantes, quando não cobram tarifas, devem enviar o valor 0.00 sinalizando que para aquela taxa não há cobrança pelo serviço.
                - **Taxa**: Percentual de clientes em cada faixa.
                - **Termos e Condições**: Link para os termos e condições do empréstimo.
                - **Tipo de Pessoa**: Indica se o empréstimo é para pessoa física ou jurídica.
                """
            )
    else:
        logger.warning("No data available for loans.")
        st.write("No data available for loans.")

except Exception as e:
    logger.error(f"Error fetching loans analytics: {e}")
    st.error(f"Unable to fetch loans data. {e}")
