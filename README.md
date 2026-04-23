Gov Semantic: Anotação Semântica de APIs Governamentais
O projeto Gov Semantic é uma iniciativa voltada para a interoperabilidade de dados abertos legislativos. Ele apresenta um método para o alinhamento de campos de APIs Governamentais do Brasil por meio da adição de uma tag semântica, gerada a partir de concenso de especialistas, facilitando a integração de dados e a transparência pública.

📂 Estrutura do Repositório
O repositório está organizado conforme a estrutura abaixo:

📊 Dataset ShowCase
Esta pasta contém os principais artefatos de dados e validação do projeto:

GovSemantic - Gold Dataset.json: O conjunto de dados padrão-ouro (Gold Standard), com as tag semânticas, validado por especialistas.

APIs.zip: Coleção de especificações OpenAPI 3.0.

code_alpha.py: Script Python para o cálculo da concordância inter-anotadores (Alpha de Krippendorff).

🌐 Plataforma de Anotação (Web App)
Arquivos responsáveis pelo funcionamento da ferramenta de coleta:

app.py: Servidor backend desenvolvido em Flask.

public/: Contém os arquivos estáticos (frontend), incluindo as interfaces de anotação.

requirements.txt: Dependências necessárias para rodar o projeto.

Procfile: Configuração para implantação no serviço Render.

🚀 Resumo Técnico
Metodologia de Anotação
O Gov Semantic utiliza uma abordagem focada em schema matching. A ferramenta permite que especialistas realizem anotações de forma assíncrona, persistindo as sugestões semânticas diretamente nos contratos OpenAPI das APIs, garantindo que a semântica e a estrutura do dado caminhem juntas.

Validação Estatística
A confiabilidade do mapeamento foi medida através do Alpha de Krippendorff, utilizando a biblioteca simpledorff. O cálculo processou o universo total de 335 campos das APIs avaliadas, assegurando a robustez da concordância global dos especialistas.

Infraestrutura
O projeto utiliza MongoDB Atlas devido à sua natureza schema-less, permitindo acomodar a volatilidade dos metadados governamentais e o armazenamento dinâmico das anotações sem a necessidade de migrações estruturais constantes.

💡 Casos de Uso Sugeridos
Este repositório fornece insumos para:

Treinamento de LLMs/NLP: Fine-tuning de modelos para o domínio governamental e legislativo.

Benchmarking: Testes de sistemas automatizados de alinhamento de ontologias.

Integração de Dados: Desenvolvimento de ferramentas de interoperabilidade para dados abertos.

🎓 Contexto Acadêmico
Desenvolvido como parte de pesquisa de mestrado em Tecnologia da Informação - IFPB, focado em Web Semântica e Governo Aberto.

Mantenha os dados abertos, mantenha a transparência.
