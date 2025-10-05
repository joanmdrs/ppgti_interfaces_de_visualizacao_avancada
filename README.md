# 🩺 Projeto de Realidade Virtual para Práticas Fisioterapêuticas  

**Disciplina:** PPGTI2003 - Interfaces de Visualização Avançada  
**Docente:** Prof. Rummenigge Rudson Dantas  
**Discente:** Joan de Azevedo Medeiros  

---

## 📌 Contexto  

O professor **Ênio**, do Departamento de Fisioterapia da UFRN, necessita de uma aplicação de **Realidade Virtual (RV)** personalizada para apoiar o ensino e a prática fisioterapêutica.  

Atualmente, ele utiliza um software comercial (**Active Arcade**) que auxilia na captura de movimentos das mãos, mas não foi projetado para uso clínico e **não disponibiliza dados estruturados sobre os pacientes**.  

O objetivo é criar uma solução interativa, precisa e acessível, capaz de registrar dados clínicos e facilitar o acompanhamento e a evolução dos pacientes de forma eficiente.  

---

## 🛑 Problema  

- O software comercial utilizado não é específico para fins clínicos.  
- Não há armazenamento estruturado dos dados dos pacientes.  
- A coleta e análise das informações são realizadas manualmente, por observação, o que torna o processo:  
  - menos preciso;  
  - mais trabalhoso;  
  - limitado em termos de acompanhamento e evolução do paciente.  

---

## 💡 Solução Proposta  

A aplicação será desenvolvida para **captura de movimentos em realidade virtual**, com foco fisioterapêutico, permitindo registrar, analisar e acompanhar dados dos pacientes de forma estruturada.  

### Características da Solução  

- **Interação personalizada:** captura de movimentos das mãos e braços do paciente.  
- **Registro de dados clínicos:** armazenamento estruturado das informações para análise posterior.  
- **Feedback em tempo real:** reforço visual e sonoro para correção de movimentos.  
- **Foco educacional e clínico:** acompanhamento da evolução do paciente e suporte ao ensino de técnicas fisioterapêuticas.  

---

## 🧪 Procedimentos Simulados  

### 1. Exercícios de mãos e punhos  

- Captura do movimento completo da mão.  
- Avaliação da amplitude, velocidade e precisão dos gestos.  
- Feedback visual para correção em tempo real.  

---

## 🚀 Como Executar o Projeto  

Este projeto utiliza **Python**, **Flask**, **SQLAlchemy** (para o banco de dados) e as bibliotecas de Visão Computacional **OpenCV** e **MediaPipe**.  

Siga os passos abaixo para configurar e iniciar o servidor.  

### 1. Configuração do Ambiente  

Recomenda-se o uso de um ambiente virtual (`venv`) para isolar as dependências do projeto.  

**Crie e ative o ambiente virtual:**  

```bash
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
.env\Scriptsctivate     # Windows
```

**Instale as dependências:**  

Assumindo que o arquivo `requirements.txt` contenha Flask, SQLAlchemy, OpenCV, MediaPipe e NumPy, execute:  

```bash
pip install -r requirements.txt
```

Caso não tenha o `requirements.txt`, instale manualmente:  

```bash
pip install Flask Flask-SQLAlchemy opencv-python mediapipe numpy
```

---

### 2. Execução  

O ponto de entrada principal é o arquivo `app.py`.  

**Configuração inicial do banco de dados (SQLite):**  
Se esta for a primeira execução, ou se você adicionou novas colunas (como `max_rom`), delete o arquivo de banco de dados local antes de rodar o servidor, para garantir que as tabelas sejam recriadas corretamente.  

```bash
rm fisioterapia_data.db
```

**Inicie o servidor:**  

```bash
python app.py
```

**Acesse a aplicação:**  
O servidor será iniciado na porta **5000** (a menos que configurado de outra forma).  
Abra o navegador e acesse:  

👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## ⚠️ Notas sobre a Câmera e o Feedback Nativo  

Ao clicar em **“Executar”** para iniciar um exercício, o sistema tentará abrir a câmera do dispositivo.  

Uma janela nativa do OpenCV (`cv2.imshow`) será exibida com o **feedback em tempo real** — incluindo o rastreamento das mãos e o medidor de progresso.  
Essa funcionalidade é executada em uma **thread separada** (`tracking_thread_function`).  

Para encerrar a sessão, clique no botão **“Parar Sessão”** na interface web.  
