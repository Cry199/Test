# -*- coding: utf-8 -*-

import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

# --- CONFIGURAÇÕES GERAIS DE LANÇAMENTO ---
# Altere os valores aqui para mudar o comportamento do robô sem mexer na lógica.
CONFIG = {
    "ITAU": {
        "conta": "10366",
        "historico": "343"
    },
    "REDE_CREDITO": {
        "limite_valor": 1000,
        "conta_acima_limite": "4002",
        "conta_abaixo_limite": "10366",
        "historico_acima_limite": "262",
        "historico_abaixo_limite": "343"
    }
}


# --- FIM DAS CONFIGURAÇÕES ---


# --- (Funções da interface gráfica) ---
def pegar_credenciais_gui():
    root = tk.Tk()
    root.withdraw()
    usuario = simpledialog.askstring("Login", "Digite seu usuário (ou e-mail):", parent=root)
    if not usuario: return None, None
    senha = simpledialog.askstring("Login", "Digite sua senha:", show='*', parent=root)
    if senha is None: return None, None
    root.destroy()
    return usuario, senha


def pegar_lancamentos_gui(data_atual):
    root = tk.Tk()
    root.title(f"Lançamentos para a data: {data_atual}")
    root.geometry("500x400")
    resultado = {"texto": ""}

    def ao_clicar_ok():
        resultado["texto"] = txt_lancamentos.get("1.0", tk.END)
        root.destroy()

    def ao_clicar_cancelar():
        resultado["texto"] = None
        root.destroy()

    lbl_instrucao = tk.Label(root, text=f"Cole aqui os lançamentos da data {data_atual}:", font=("Arial", 12))
    lbl_instrucao.pack(pady=10)
    txt_lancamentos = scrolledtext.ScrolledText(root, width=58, height=15, font=("Arial", 10))
    txt_lancamentos.pack(pady=5, padx=10)
    frame_botoes = tk.Frame(root)
    frame_botoes.pack(pady=10)
    btn_ok = tk.Button(frame_botoes, text="OK", command=ao_clicar_ok, width=10)
    btn_ok.pack(side=tk.LEFT, padx=10)
    btn_cancelar = tk.Button(frame_botoes, text="Cancelar", command=ao_clicar_cancelar, width=10)
    btn_cancelar.pack(side=tk.LEFT, padx=10)
    root.mainloop()
    return resultado["texto"]


def pegar_data_gui():
    root = tk.Tk()
    root.withdraw()
    data = simpledialog.askstring("Data", "Qual a data dos próximos lançamentos? (ex: 12/06)", parent=root)
    root.destroy()
    if data and re.match(r'^\d{2}/\d{2}$', data):
        return data
    return None


# --- Funções de Lógica de Negócio ---
def preencher_e_salvar_lancamento(driver, linha_atual, data_atual, codigo_da_conta, codigo_do_historico):
    """
    Função reutilizável para preencher e salvar um único lançamento.
    Recebe o código da conta e o código do histórico como argumentos.
    """
    print(f"Iniciando preenchimento para a linha: '{linha_atual.strip()}' na data {data_atual}")
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "nova"))).click()
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "salvar-sair")))
    match_valor = re.search(r'([\d.,]+)$', linha_atual)

    # ... (código para preencher data e centro de custo continua igual) ...
    campo_data = driver.find_element(By.ID, "data")
    campo_data.click()
    campo_data.clear()
    for char in data_atual:
        campo_data.send_keys(char)
        time.sleep(0.05)

    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='nomeCentroDeCusto']/a"))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
        (By.XPATH, "//div[contains(@class, 'select2-drop-active')]//input[@type='search']"))).send_keys(
        "SANTUÁRIO SÃO JUDAS TADEU")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH,
                                                                "//div[contains(@class, 'select2-result-label')][contains(., 'SANTUÁRIO SÃO JUDAS TADEU')]"))).click()

    if match_valor:
        valor_str = match_valor.group(1)
        if codigo_da_conta:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contaId_value"))).send_keys(
                codigo_da_conta)
            xpath_resultado_conta = f"//div[@id='contaId_dropdown']//div[contains(@class, 'angucomplete-row') and contains(., '{codigo_da_conta}')]"
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_resultado_conta))).click()

        # --- NOVA VALIDAÇÃO ADICIONADA AQUI ---
        if codigo_da_conta == "10366":
            print("Código 10366 detectado. Preenchendo o campo 'Banco'...")
            # 1. Clica para abrir o dropdown de Banco
            xpath_abrir_banco = "//div[@id='banco']//a[contains(@class, 'select2-choice')]"
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_abrir_banco))).click()

            # 2. Clica na primeira opção que aparecer na lista
            xpath_primeira_opcao_banco = "//li[contains(@class, 'ui-select-choices-row')][1]"
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_primeira_opcao_banco))).click()
            print("Campo 'Banco' preenchido com a primeira opção.")
        # --- FIM DA NOVA VALIDAÇÃO ---

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "valor"))).send_keys(
            valor_str.replace('.', ''))

        if codigo_do_historico:
            # ... (o resto da função continua exatamente como estava) ...
            print(f"Selecionando Histórico Padrão com código: {codigo_do_historico}")
            dropdown_container = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='historico']/a")))
            driver.execute_script("arguments[0].click();", dropdown_container)
            busca_historico_xpath = "//div[contains(@class, 'select2-drop-active')]//input[@type='search']"
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, busca_historico_xpath)))
            js_script_hist = f"""
            var searchInput = document.querySelector("div.select2-drop-active input.select2-input");
            if (searchInput) {{
                searchInput.value = '{codigo_do_historico}';
                searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                searchInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            """
            driver.execute_script(js_script_hist)
            resultado_filtrado_xpath = (
                f"//div[@class='select2-result-label ui-select-choices-row-inner'][div[contains(text(), '{codigo_do_historico}')]]")
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, resultado_filtrado_xpath))).click()

    time.sleep(0.5)
    entrada_radio_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "entrada")))
    driver.execute_script("arguments[0].click();", entrada_radio_button)
    botao_salvar_sair = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "salvar-sair")))
    driver.execute_script("arguments[0].click();", botao_salvar_sair)
    WebDriverWait(driver, 15).until(EC.invisibility_of_element_located((By.ID, "salvar-sair")))
    print(f"Lançamento da linha '{linha_atual.strip()}' concluído com sucesso.")

# --- FLUXO PRINCIPAL DO SCRIPT ---
lista_de_tarefas = []
while True:
    data_atual = pegar_data_gui()
    if not data_atual: break
    lancamentos_atuais = pegar_lancamentos_gui(data_atual)
    if not lancamentos_atuais or not lancamentos_atuais.strip():
        messagebox.showwarning("Aviso",
                               f"Nenhum lançamento inserido para a data {data_atual}. Esta data será ignorada.")
    else:
        lista_de_tarefas.append({"data": data_atual, "lancamentos": lancamentos_atuais})
    if not messagebox.askyesno("Continuar?", "Deseja inserir lançamentos para OUTRA data?"):
        break

if not lista_de_tarefas:
    messagebox.showinfo("Encerrado", "Nenhuma tarefa foi adicionada. O programa será encerrado.")
    exit()

print("Coleta de dados finalizada. Tarefas a processar:", len(lista_de_tarefas))
usuario, senha = pegar_credenciais_gui()
if not usuario or senha is None:
    messagebox.showwarning("Cancelado", "Login cancelado.")
    exit()

print("\nCredenciais recebidas. Iniciando a automação...")
driver = None
try:
    driver = webdriver.Chrome()
    driver.maximize_window()
    print("Carregando a página e fazendo login...")
    driver.get("https://diocesedesantoamaro.sistemapastoral.com.br/login")
    try:
        campo_usuario = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "login-username")))
        campo_senha = driver.find_element(By.ID, "login-password")
    except TimeoutException:
        campo_usuario = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "usuario")))
        campo_senha = driver.find_element(By.ID, "senha")
    campo_usuario.send_keys(usuario)
    campo_senha.send_keys(senha)
    botao_login = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Entrar')]")))
    driver.execute_script("arguments[0].click();", botao_login)
    print("Login enviado. Aguardando a página carregar...")
    time.sleep(3)

    # <<< FASE 2: PROCESSAMENTO DA LISTA DE TAREFAS (COM CONFIG) >>>
    print("\nIniciando lançamentos automáticos...")
    for tarefa in lista_de_tarefas:
        data_da_tarefa = tarefa["data"]
        lancamentos_da_tarefa = tarefa["lancamentos"]
        print(f"\n--- Processando lançamentos para a data: {data_da_tarefa} ---")
        linhas_para_processar = lancamentos_da_tarefa.strip().split('\n')

        for linha in linhas_para_processar:
            if not linha.strip(): continue
            try:
                match_valor = re.search(r'([\d.,]+)$', linha)
                if not match_valor:
                    print(f"AVISO: Não foi possível encontrar um valor na linha '{linha.strip()}'. Pulando...")
                    continue
                valor_str = match_valor.group(1)
                valor_num = float(valor_str.replace('.', '').replace(',', '.'))

                # --- PRIMEIRO LANÇAMENTO: BANCO ITAU ---
                print("\n>>> LANÇAMENTO NO BANCO ITAU <<<")
                driver.get("https://diocesedesantoamaro.sistemapastoral.com.br/movimentacao-contabil-do-banco")
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable(
                    (By.XPATH, "//tr[contains(., 'BANCO ITAU UNIBANCO S/A.') and contains(., 'CORRENTE')]"))).click()
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "concluir"))).click()

                codigo_itau = CONFIG["ITAU"]["conta"]
                historico_itau = CONFIG["ITAU"]["historico"]
                preencher_e_salvar_lancamento(driver, linha, data_da_tarefa, codigo_itau, historico_itau)

                # --- SEGUNDO LANÇAMENTO: REDE-CREDITO ---
                print("\n>>> LANÇAMENTO NA REDE-CREDITO <<<")
                driver.get("https://diocesedesantoamaro.sistemapastoral.com.br/movimentacao-contabil-do-banco")
                xpath_rede_credito = "//tr[contains(., 'REDE-CREDITO') and contains(., 'CARTAO CREDITO')]"
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath_rede_credito))).click()
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "concluir"))).click()

                cfg_rede = CONFIG["REDE_CREDITO"]
                if valor_num >= cfg_rede["limite_valor"]:
                    codigo_rede = cfg_rede["conta_acima_limite"]
                    historico_rede = cfg_rede["historico_acima_limite"]
                else:
                    codigo_rede = cfg_rede["conta_abaixo_limite"]
                    historico_rede = cfg_rede["historico_abaixo_limite"]

                print(f"Valor R$ {valor_num:.2f} detectado. Usando Conta: {codigo_rede}, Histórico: {historico_rede}")
                preencher_e_salvar_lancamento(driver, linha, data_da_tarefa, codigo_rede, historico_rede)

            except Exception as e:
                print(f"!!!!!!!!!!!!!! ERRO CRÍTICO !!!!!!!!!!!!!!")
                print(f"Ocorreu um erro ao processar a linha: {linha.strip()}")
                print(f"Erro: {type(e).__name__} - {e}")
                print(f"A automação continuará com a próxima linha.")

    print("\nAutomação concluída!")

except Exception as e:
    messagebox.showerror("Erro Crítico",
                         f"Ocorreu um erro geral na automação.\n\nErro: {e}\n\nO programa será encerrado.")
finally:
    if 'driver' in locals() and driver:
        print("Fechando o navegador.")
        driver.quit()
    exit()
