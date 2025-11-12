// URL da API no Render (deve ser a mesma do index.html)
const API_BASE_URL = 'https://api-mestrado-anotacao.onrender.com';

// 1. Obter dados da sessão (salvos pelo index.html)
const specialistId = sessionStorage.getItem('specialist_id');
const specialistName = sessionStorage.getItem('specialist_name');
const collectionName = sessionStorage.getItem('collection_name');

// 2. Elementos do DOM
const navInfo = document.getElementById('nav-info');
const card = document.getElementById('annotation-card');
const cardHeader = document.getElementById('card-header');
const itemContext = document.getElementById('item-context');
const itemDescription = document.getElementById('item-description');
const annotationForm = document.getElementById('annotation-form');
const sugestoesContainer = document.getElementById('sugestoes-container');
const saveBtn = document.getElementById('save-btn');
const finishedMessage = document.getElementById('finished-message');

let currentItemId = null; // Guarda o _id do item atual

// 3. Função: Buscar o Próximo Item
async function fetchNextItem() {
    // Mostrar estado de carregamento
    card.setAttribute('aria-busy', 'true');
    cardHeader.textContent = 'Carregando próximo item...';
    annotationForm.style.display = 'none';
    finishedMessage.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/next_item?collection_name=${collectionName}&specialist_id=${specialistId}`);
        
        if (response.status === 404) {
            // Nenhum item restante!
            showFinishedMessage();
            return;
        }
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.message || 'Erro ao buscar item.');
        }

        const item = await response.json();
        currentItemId = item._id; // Salva o ID do item atual
        displayItem(item);

    } catch (error) {
        console.error('Erro em fetchNextItem:', error);
        cardHeader.innerHTML = `<span style="color: var(--pico-color-red-500);">Erro ao carregar</span>`;
        itemDescription.textContent = `Não foi possível carregar o próximo item. Verifique sua conexão ou contate o administrador. (Erro: ${error.message})`;
        card.setAttribute('aria-busy', 'false');
    }
}

// 4. Função: Exibir o Item na Tela
function displayItem(item) {
    cardHeader.innerHTML = `Anotando: <strong>${item.campo_nome}</strong>`;
    
    // Preenche o contexto
    itemContext.innerHTML = `
        <li><strong>API:</strong> ${item.api_nome}</li>
        <li><strong>Endpoint:</strong> ${item.endpoint_method} ${item.endpoint_path}</li>
        <li><strong>Tipo:</strong> ${item.campo_tipo || 'N/A'}</li>
        <li><strong>Exemplo:</strong> <code>${item.campo_exemplo || 'N/A'}</code></li>
    `;
    
    // Preenche a descrição
    itemDescription.textContent = item.campo_descricao;

    // Preenche o formulário de anotação
    sugestoesContainer.innerHTML = ''; // Limpa opções anteriores

    // Adiciona as 3 sugestões
    item.sugestoes_llm.forEach((sugestao, index) => {
        const id = `radio-sugestao-${index}`;
        sugestoesContainer.innerHTML += `
            <fieldset>
                <label for="${id}">
                    <input type="radio" id="${id}" name="anotacao" value="${sugestao}" ${index === 0 ? 'checked' : ''}>
                    ${sugestao}
                </label>
            </fieldset>
        `;
    });

    // Adiciona a opção "Outra"
    sugestoesContainer.innerHTML += `
        <fieldset id="radio-outro">
            <label for="radio-outro-input">
                <input type="radio" id="radio-outro-input" name="anotacao" value="__outro__">
                Outra (especificar)
            </label>
            <div id="outro-container">
                <input type="text" id="outro-input" name="anotacao_outra" placeholder="Digite a tag correta aqui..." autocomplete="off">
            </div>
        </fieldset>
    `;

    // Adiciona lógica para o campo "Outra"
    const outroInput = document.getElementById('outro-input');
    const outroRadio = document.getElementById('radio-outro-input');

    // Se o usuário digitar, seleciona automaticamente o rádio "Outra"
    outroInput.addEventListener('focus', () => {
        outroRadio.checked = true;
    });

    // Se o usuário clicar em outro rádio, limpa o campo "Outra"
    sugestoesContainer.querySelectorAll('input[type="radio"]').forEach(radio => {
        if (radio.id !== 'radio-outro-input') {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    outroInput.value = '';
                }
            });
        }
    });

    // Remove o estado de carregamento e mostra o formulário
    card.setAttribute('aria-busy', 'false');
    annotationForm.style.display = 'block';
    saveBtn.disabled = false;
    saveBtn.setAttribute('aria-busy', 'false');
}

// 5. Função: Lidar com o Envio do Formulário
async function handleFormSubmit(e) {
    e.preventDefault();
    saveBtn.disabled = true;
    saveBtn.setAttribute('aria-busy', 'true');

    let escolhaFinal = '';
    
    // Descobre qual opção foi escolhida
    const formData = new FormData(annotationForm);
    const escolhaRadio = formData.get('anotacao');

    if (escolhaRadio === '__outro__') {
        escolhaFinal = formData.get('anotacao_outra');
        if (!escolhaFinal || escolhaFinal.trim() === '') {
            alert('Você selecionou "Outra", mas não especificou a tag. Por favor, digite a tag correta.');
            saveBtn.disabled = false;
            saveBtn.setAttribute('aria-busy', 'false');
            return;
        }
    } else {
        escolhaFinal = escolhaRadio;
    }

    // Envia os dados para a API
    try {
        const response = await fetch(`${API_BASE_URL}/annotate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                collection_name: collectionName,
                item_id: currentItemId,
                specialist_id: specialistId,
                escolha: escolhaFinal.trim()
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.message || 'Erro ao salvar anotação.');
        }

        // Sucesso! Busca o próximo item.
        fetchNextItem();

    } catch (error) {
        console.error('Erro em handleFormSubmit:', error);
        alert(`Erro ao salvar: ${error.message}`);
        saveBtn.disabled = false;
        saveBtn.setAttribute('aria-busy', 'false');
    }
}

// 6. Função: Mostrar Mensagem de Conclusão
function showFinishedMessage() {
    card.setAttribute('aria-busy', 'false');
    cardHeader.textContent = 'Concluído!';
    annotationForm.style.display = 'none'; // Esconde o formulário
    document.getElementById('card-body').style.display = 'none'; // Esconde o corpo
    finishedMessage.style.display = 'block'; // Mostra a mensagem final
}

// --- Inicialização da Página ---
document.addEventListener('DOMContentLoaded', () => {
    // 1. Verifica se o usuário veio do index.html
    if (!specialistId || !collectionName) {
        alert('Configuração inválida. Redirecionando para a página inicial.');
        window.location.href = 'index.html';
        return;
    }

    // 2. Personaliza a barra de navegação
    // Mapeia o nome da coleção para um nome amigável
    const apiNomes = {
        "ibge_para_anotar": "API IBGE",
        "bc_para_anotar": "API Banco Central",
        "camara_para_anotar": "API Câmara",
        "tse_para_anotar": "API TSE",
        "cgu_para_anotar": "API CGU",
        "senado_para_anotar": "API Senado"
    };
    navInfo.textContent = `Especialista: ${specialistName} | Anotando: ${apiNomes[collectionName] || collectionName}`;

    // 3. Adiciona o listener ao formulário
    annotationForm.addEventListener('submit', handleFormSubmit);

    // 4. Busca o primeiro item
    fetchNextItem();
});