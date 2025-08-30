# -*- coding: utf-8 -*-

import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext


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

# <<< FUNÇÃO MODIFICADA PARA MOSTRAR A DATA NO TÍTULO >>>
def pegar_lancamentos_gui(data_atual):
    root = tk.Tk()
    root.title(f"Lançamentos para a data: {data_atual}") # Título dinâmico
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

# --- Funções de Lógica de Negócio (Sem alterações) ---
def determinar_codigo_conta(valor_str):
    try:
        valor_num = float(valor_str.replace('.', '').replace(',', '.'))
    except (ValueError, AttributeError):
        return None
    if valor_num == 121: return "40011"
    elif valor_num == 12: return "40062"
    elif valor_num == 24: return "40064"
    elif valor_num >= 100: return "40002"
    elif valor_num > 20: return "40021"
    elif valor_num <= 20: return "40001"
    else: return None


def determinar_codigo_historico(valor_str):
    try:
        valor_num = float(valor_str.replace('.', '').replace(',', '.'))
    except (ValueError, AttributeError):
        return None
    if valor_num == 121: return "263"
    elif valor_num == 12: return "242"
    elif valor_num == 24: return "268"
    elif valor_num >= 100: return "262"
    elif valor_num > 20: return "229"
    elif valor_num <= 20: return "261"
    else: return None


# --- FLUXO PRINCIPAL DO SCRIPT ---

# <<< FASE 1: COLETA DE DADOS EM LOOP >>>
lista_de_tarefas = []
while True:
    data_atual = pegar_data_gui()
    if not data_atual:
        # Se o usuário cancelar a data, encerramos a coleta
        break
    
    lancamentos_atuais = pegar_lancamentos_gui(data_atual)
    if not lancamentos_atuais or not lancamentos_atuais.strip():
        messagebox.showwarning("Aviso", f"Nenhum lançamento inserido para a data {data_atual}. Esta data será ignorada.")
    else:
        # Adiciona o par (data, lançamentos) na nossa lista
        lista_de_tarefas.append({"data": data_atual, "lancamentos": lancamentos_atuais})

    # Pergunta se o usuário quer continuar
    if not messagebox.askyesno("Continuar?", "Deseja inserir lançamentos para OUTRA data?"):
        break

if not lista_de_tarefas:
    messagebox.showinfo("Encerrado", "Nenhuma tarefa foi adicionada. O programa será encerrado.")
    exit()

print("Coleta de dados finalizada. Tarefas a processar:", len(lista_de_tarefas))
# <<< FIM DA FASE 1 >>>

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

    botao_login = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Entrar')]")))
    driver.execute_script("arguments[0].click();", botao_login)
    print("Login enviado. Aguardando a página carregar...")
    time.sleep(3)

    driver.get("https://diocesedesantoamaro.sistemapastoral.com.br/movimentacao-contabil-do-banco")
    WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//tr[contains(., 'BANCO ITAU UNIBANCO S/A.') and contains(., 'CORRENTE')]"))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "concluir"))).click()
    print("Banco selecionado.")

    # <<< FASE 2: PROCESSAMENTO DA LISTA DE TAREFAS >>>
    print("\nIniciando lançamentos automáticos...")
    for tarefa in lista_de_tarefas:
        data_da_tarefa = tarefa["data"]
        lancamentos_da_tarefa = tarefa["lancamentos"]
        
        print(f"\n--- Processando lançamentos para a data: {data_da_tarefa} ---")
        linhas_para_processar = lancamentos_da_tarefa.strip().split('\n')

        for i, linha in enumerate(linhas_para_processar):
            if not linha.strip(): continue

            try:
                print(f"Processando linha {i + 1}/{len(linhas_para_processar)}: {linha.strip()}")
                WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "nova"))).click()
                WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "salvar-sair")))

                match_valor = re.search(r'([\d.,]+)$', linha)

                # <<< AQUI USAMOS A DATA CORRETA PARA CADA GRUPO >>>
                print(f"Preenchendo data: {data_da_tarefa}")
                campo_data = driver.find_element(By.ID, "data")
                campo_data.click()
                campo_data.clear()
                for char in data_da_tarefa:
                    campo_data.send_keys(char)
                    time.sleep(0.05)

                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='nomeCentroDeCusto']/a"))).click()
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'select2-drop-active')]//input[@type='search']"))).send_keys("SANTUÁRIO SÃO JUDAS TADEU")
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'select2-result-label')][contains(., 'SANTUÁRIO SÃO JUDAS TADEU')]"))).click()

                if match_valor:
                    valor_str = match_valor.group(1)
                    codigo_conta = determinar_codigo_conta(valor_str)
                    if codigo_conta:
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "contaId_value"))).send_keys(codigo_conta)
                        xpath_resultado_conta = f"//div[@id='contaId_dropdown']//div[contains(@class, 'angucomplete-row') and contains(., '{codigo_conta}')]"
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath_resultado_conta))).click()

                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "valor"))).send_keys(valor_str.replace('.', ''))
                    
                    codigo_historico = determinar_codigo_historico(valor_str)
                    if codigo_historico:
                        print(f"Selecionando Histórico Padrão com código: {codigo_historico}")
                        dropdown_container = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='historico']/a")))
                        driver.execute_script("arguments[0].click();", dropdown_container)
                        busca_historico_xpath = "//div[contains(@class, 'select2-drop-active')]//input[@type='search']"
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, busca_historico_xpath)))
                        js_script_hist = f"""
                        var searchInput = document.querySelector("div.select2-drop-active input.select2-input");
                        if (searchInput) {{
                            searchInput.value = '{codigo_historico}';
                            searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            searchInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        """
                        driver.execute_script(js_script_hist)
                        resultado_filtrado_xpath = (f"//div[@class='select2-result-label ui-select-choices-row-inner'][div[contains(text(), '{codigo_historico}')]]")
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, resultado_filtrado_xpath))).click()

                time.sleep(0.5)
                entrada_radio_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "entrada")))
                driver.execute_script("arguments[0].click();", entrada_radio_button)

                botao_salvar_sair = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "salvar-sair")))
                driver.execute_script("arguments[0].click();", botao_salvar_sair)

                WebDriverWait(driver, 15).until(EC.invisibility_of_element_located((By.ID, "salvar-sair")))
                print(f"Lançamento da linha '{linha.strip()}' concluído com sucesso.")

            except Exception as e:
                print(f"Ocorreu um erro crítico ao processar a linha: {linha.strip()}\nErro: {type(e).__name__} - {e}")
                # Lógica de recuperação e continuação... (mantida como estava)
    
    print("\nAutomação concluída!")

except Exception as e:
    messagebox.showerror("Erro Crítico", f"Ocorreu um erro geral na automação.\n\nErro: {e}\n\nO programa será encerrado.")
finally:
    if 'driver' in locals() and driver:
        print("Fechando o navegador.")
        driver.quit()
    exit()
