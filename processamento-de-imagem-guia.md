# Processamento Digital de Imagens — Guia para Professor(a)

> Material de estudo organizado para preparar aulas de Processamento de Imagem. Cobre teoria, fórmulas, exemplos de código (Python + OpenCV/NumPy) e sugestões de exercícios para cada tópico.

---

## Sumário

1. [Introdução](#1-introdução)
2. [Representação da Imagem Digital](#2-representação-da-imagem-digital)
3. [Modelos de Cor](#3-modelos-de-cor)
4. [Aquisição, Amostragem e Formatos de Arquivo](#4-aquisição-amostragem-e-formatos-de-arquivo)
5. [Operações Pontuais (Point Processing)](#5-operações-pontuais-point-processing)
6. [Histograma](#6-histograma)
7. [Filtragem Espacial (Convolução)](#7-filtragem-espacial-convolução)
8. [Detecção de Bordas](#8-detecção-de-bordas)
9. [Ruído e Restauração](#9-ruído-e-restauração)
10. [Morfologia Matemática](#10-morfologia-matemática)
11. [Transformações Geométricas](#11-transformações-geométricas)
12. [Domínio da Frequência](#12-domínio-da-frequência)
13. [Segmentação de Imagens](#13-segmentação-de-imagens)
14. [Compressão de Imagens](#14-compressão-de-imagens)
15. [Panorama: Visão Computacional e Deep Learning](#15-panorama-visão-computacional-e-deep-learning)
16. [Ferramentas Práticas (Python)](#16-ferramentas-práticas-python)
17. [Sugestão de Cronograma de Aulas](#17-sugestão-de-cronograma-de-aulas)
18. [Banco de Exercícios](#18-banco-de-exercícios)
19. [Referências](#19-referências)

---

## 1. Introdução

**Processamento Digital de Imagens (PDI)** é a área que estuda algoritmos para manipular, analisar e melhorar imagens representadas em forma digital (matrizes de números).

### O que é uma imagem digital?
Uma imagem digital é uma função `f(x, y)` onde `x` e `y` são coordenadas espaciais e o valor de `f` naquele ponto é a **intensidade** (brilho ou cor). Quando `x`, `y` e os valores de intensidade são discretos (números inteiros finitos), chamamos de **imagem digital**.

### PDI vs. Visão Computacional
- **Processamento de Imagem**: imagem entra → imagem sai (ex.: remover ruído, melhorar contraste, aplicar filtro).
- **Visão Computacional**: imagem entra → informação/decisão sai (ex.: "há um rosto nesta imagem?", "qual é a placa do carro?").
Na prática as duas áreas se sobrepõem bastante — segmentação e detecção de bordas, por exemplo, são usadas nas duas.

### Aplicações comuns
- Medicina (raio-X, tomografia, ressonância)
- Sensoriamento remoto e satélites
- Indústria (inspeção de qualidade)
- Segurança (reconhecimento facial, OCR)
- Fotografia e edição (Instagram, Photoshop)
- Carros autônomos, robótica

---

## 2. Representação da Imagem Digital

### Pixel
Um **pixel** (*picture element*) é a menor unidade de uma imagem digital — um "quadradinho" com um valor numérico (ou um vetor de valores, no caso de imagens coloridas).

### Resolução
Número de pixels em largura × altura. Ex.: `1920 x 1080`. Quanto maior, mais detalhes — e mais espaço em memória.

### Profundidade de bits (*bit depth*)
Quantos bits são usados para representar a intensidade de cada pixel:
- **1 bit** → imagem binária (preto/branco puro): 2 valores
- **8 bits** → escala de cinza: 256 valores (0 a 255)
- **24 bits** (8+8+8) → colorida RGB: ~16,7 milhões de cores

### Tipos de imagem
| Tipo | Descrição | Exemplo de valor de pixel |
|---|---|---|
| Binária | Só 0 ou 1 (preto/branco) | `0` ou `1` |
| Escala de cinza | Um único canal, 0–255 | `137` |
| Colorida (RGB) | Três canais: vermelho, verde, azul | `(137, 45, 200)` |
| Indexada | Valor aponta para uma paleta de cores | índice `12` → cor da paleta |

### Representação matricial
Uma imagem em escala de cinza de 4×3 pixels é literalmente uma matriz:

```
[ 12  45 200 130]
[ 33  90  10 255]
[  0 128 128  64]
```

Em Python isso é um array NumPy de shape `(altura, largura)`. Uma imagem RGB tem shape `(altura, largura, 3)`.

---

## 3. Modelos de Cor

### RGB (Red, Green, Blue)
Modelo aditivo usado em telas. Cada pixel = combinação de intensidades de vermelho, verde e azul (0–255 cada).
- `(255, 0, 0)` = vermelho puro
- `(255, 255, 255)` = branco
- `(0, 0, 0)` = preto

### CMYK (Cyan, Magenta, Yellow, Key/Black)
Modelo **subtrativo**, usado em impressão.

### HSV / HSL (Matiz, Saturação, Valor/Luminosidade)
Separa a **cor** (Hue) da **intensidade** (Value/Lightness). Muito útil para tarefas como "selecionar todos os pixels vermelhos", pois isola a cor da iluminação.
- **H (Hue)**: 0–360° (a cor em si, no círculo cromático)
- **S (Saturation)**: 0–100% (quão "pura"/vibrante é a cor)
- **V (Value)**: 0–100% (brilho)

### YCbCr
Separa **luminância** (Y, brilho) de **crominância** (Cb, Cr — informação de cor). Usado em compressão JPEG e vídeo, porque o olho humano é mais sensível a variações de brilho do que de cor.

### Escala de cinza a partir de RGB
Fórmula ponderada (considera a sensibilidade do olho humano a cada cor):

```
Cinza = 0.299·R + 0.587·G + 0.114·B
```

```python
import cv2
img = cv2.imread("foto.jpg")
cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
```

---

## 4. Aquisição, Amostragem e Formatos de Arquivo

### Amostragem e quantização
- **Amostragem**: discretizar o espaço (quantos pontos/pixels vamos capturar).
- **Quantização**: discretizar a intensidade (quantos níveis de cinza/cor vamos usar).

Amostragem insuficiente → imagem "pixelada" (baixa resolução).
Quantização insuficiente → efeito de "faixas" (*banding*), poucos níveis de cor visíveis.

### Formatos de arquivo — sem perdas vs. com perdas
| Formato | Compressão | Uso típico |
|---|---|---|
| BMP | Nenhuma | Raramente usado hoje, arquivos grandes |
| PNG | Sem perdas | Imagens com transparência, gráficos, texto |
| GIF | Sem perdas, paleta limitada (256 cores) | Animações simples |
| JPEG | Com perdas | Fotografias (compressão alta, menor arquivo) |
| TIFF | Sem/com perdas | Uso profissional/impressão |
| WebP | Ambos | Web moderna |

---

## 5. Operações Pontuais (Point Processing)

São transformações onde **o novo valor de um pixel depende apenas do valor original daquele mesmo pixel** (não dos vizinhos). Forma geral: `g(x,y) = T(f(x,y))`.

### Negativo
```
g = 255 - f
```
```python
negativo = 255 - cinza
```

### Brilho (soma/subtração de uma constante)
```
g = f + c
```
```python
mais_brilho = cv2.add(img, (30,30,30,0))  # soma 30 em cada canal, satura em 255
```

### Contraste (multiplicação por uma constante)
```
g = f * alpha        # alpha > 1 aumenta contraste, < 1 diminui
```
```python
mais_contraste = cv2.convertScaleAbs(img, alpha=1.5, beta=0)
```
`alpha` controla contraste, `beta` controla brilho — é comum combinar os dois: `g = alpha*f + beta`.

### Transformação logarítmica
Expande valores baixos (sombras), comprime valores altos. Útil para realçar detalhes em regiões escuras.
```
g = c · log(1 + f)
```

### Transformação de potência / gamma
```
g = c · f^γ
```
- `γ < 1` → clareia a imagem (expande sombras)
- `γ > 1` → escurece a imagem (expande realces)

Usada em **correção gama** de monitores e câmeras.

### Limiarização (thresholding)
Transforma a imagem em binária: pixels acima de um limiar viram branco, abaixo viram preto.
```
g = 255 se f > T,  senão 0
```
```python
_, binaria = cv2.threshold(cinza, 127, 255, cv2.THRESH_BINARY)
```

---

## 6. Histograma

O **histograma** de uma imagem é um gráfico que mostra a frequência de cada nível de intensidade (0–255). É a principal ferramenta para entender contraste e exposição de uma imagem sem olhar para ela diretamente.

- Histograma concentrado à esquerda → imagem escura
- Histograma concentrado à direita → imagem clara
- Histograma espalhado por toda a faixa → bom contraste

```python
import matplotlib.pyplot as plt
hist = cv2.calcHist([cinza], [0], None, [256], [0, 256])
plt.plot(hist)
plt.show()
```

### Equalização de histograma
Redistribui as intensidades para que fiquem mais uniformemente espalhadas, aumentando o contraste global — muito usado em imagens médicas e de baixo contraste.

```python
equalizada = cv2.equalizeHist(cinza)
```

### CLAHE (Equalização adaptativa)
Versão que equaliza por regiões locais (evita superexposição em imagens com áreas muito claras e escuras ao mesmo tempo).
```python
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
resultado = clahe.apply(cinza)
```

---

## 7. Filtragem Espacial (Convolução)

Diferente das operações pontuais, aqui **o novo valor de um pixel depende dele e de seus vizinhos**, usando uma pequena matriz chamada **kernel** (ou máscara/filtro), tipicamente 3×3 ou 5×5.

### Como funciona a convolução
O kernel "desliza" sobre a imagem; em cada posição, multiplica os valores do kernel pelos pixels correspondentes e soma tudo — esse valor vira o novo pixel central.

```
novo_pixel = Σ Σ kernel(i,j) · imagem(x+i, y+j)
```

### Filtro de suavização (blur) — média
Kernel 3×3 de média (todos os pesos iguais, soma = 1):
```
1/9 * [1 1 1]
      [1 1 1]
      [1 1 1]
```
```python
suavizada = cv2.blur(img, (5,5))
```
Reduz ruído, mas também borra bordas e detalhes.

### Filtro Gaussiano
Como a média, mas dá mais peso ao pixel central (segue uma curva de distribuição normal). Produz um borrão mais "natural".
```python
gauss = cv2.GaussianBlur(img, (5,5), sigmaX=0)
```

### Filtro de mediana
Em vez de média, pega a **mediana** dos valores na vizinhança. Excelente para remover ruído "sal e pimenta" preservando bordas melhor que a média.
```python
mediana = cv2.medianBlur(img, 5)
```

### Filtro de realce (sharpening)
Kernel que acentua as diferenças entre um pixel e seus vizinhos:
```
[ 0 -1  0]
[-1  5 -1]
[ 0 -1  0]
```
```python
import numpy as np
kernel_sharpen = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
nitida = cv2.filter2D(img, -1, kernel_sharpen)
```

---

## 8. Detecção de Bordas

Bordas são regiões onde há **mudança abrupta de intensidade** — geralmente correspondem a contornos de objetos.

### Gradiente
A borda é detectada calculando a derivada (gradiente) da imagem. Quanto maior o gradiente, mais forte a borda.

### Sobel
Aplica dois kernels (um para gradiente horizontal, outro vertical) e combina os resultados:
```
Sobel X:            Sobel Y:
[-1 0 1]            [-1 -2 -1]
[-2 0 2]            [ 0  0  0]
[-1 0 1]            [ 1  2  1]
```
```python
sobel_x = cv2.Sobel(cinza, cv2.CV_64F, 1, 0, ksize=3)
sobel_y = cv2.Sobel(cinza, cv2.CV_64F, 0, 1, ksize=3)
magnitude = cv2.magnitude(sobel_x, sobel_y)
```

### Laplaciano
Derivada de segunda ordem — detecta bordas em todas as direções de uma vez, mas é mais sensível a ruído.
```python
laplaciano = cv2.Laplacian(cinza, cv2.CV_64F)
```

### Canny (o algoritmo mais usado na prática)
Pipeline completo: suavização Gaussiana → cálculo de gradiente (Sobel) → supressão de não-máximos → limiarização com histerese (dois limiares). Resulta em bordas finas e bem definidas.
```python
bordas = cv2.Canny(cinza, threshold1=100, threshold2=200)
```

---

## 9. Ruído e Restauração

### Tipos comuns de ruído
- **Sal e pimenta**: pixels aleatórios totalmente pretos ou brancos.
- **Ruído Gaussiano**: variação aleatória com distribuição normal em todos os pixels (típico de sensores de câmera).

### Filtros de remoção
| Tipo de ruído | Melhor filtro |
|---|---|
| Sal e pimenta | Mediana |
| Gaussiano | Gaussiano ou média |
| Preservando bordas | Filtro bilateral |

```python
# Filtro bilateral: suaviza mas preserva bordas (usa peso espacial + peso de intensidade)
bilateral = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
```

---

## 10. Morfologia Matemática

Operações aplicadas principalmente em **imagens binárias**, usando um **elemento estruturante** (kernel de forma definida, ex.: quadrado, cruz).

- **Erosão**: "encolhe" objetos brancos — remove ruído pequeno, separa objetos conectados.
- **Dilatação**: "expande" objetos brancos — preenche buracos pequenos.
- **Abertura** (erosão seguida de dilatação): remove ruído mantendo o tamanho do objeto.
- **Fechamento** (dilatação seguida de erosão): fecha pequenos buracos/lacunas.

```python
kernel = np.ones((5,5), np.uint8)
erosao = cv2.erode(binaria, kernel, iterations=1)
dilatacao = cv2.dilate(binaria, kernel, iterations=1)
abertura = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, kernel)
fechamento = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel)
```

---

## 11. Transformações Geométricas

Mudam a **posição** dos pixels, não seus valores.

- **Translação**: desloca a imagem em x/y.
- **Rotação**: gira em torno de um ponto (geralmente o centro).
- **Escala (resize)**: aumenta/diminui o tamanho.
- **Espelhamento (flip)**: inverte horizontal ou verticalmente.

Ao redimensionar ou rotacionar, é preciso **interpolar** valores para os novos pixels (vizinho mais próximo, bilinear, bicúbica).

```python
# Redimensionar
maior = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)

# Rotacionar 45 graus em torno do centro
(h, w) = img.shape[:2]
M = cv2.getRotationMatrix2D((w/2, h/2), 45, 1.0)
rotacionada = cv2.warpAffine(img, M, (w, h))
```

---

## 12. Domínio da Frequência

Toda imagem pode ser decomposta em componentes de frequência usando a **Transformada de Fourier**: regiões de variação lenta de intensidade (fundo, céu) = baixa frequência; bordas e detalhes finos = alta frequência.

- **Filtro passa-baixa** no domínio da frequência = suaviza a imagem (efeito de blur).
- **Filtro passa-alta** no domínio da frequência = realça bordas e detalhes.

```python
f = np.fft.fft2(cinza)
fshift = np.fft.fftshift(f)
espectro = 20 * np.log(np.abs(fshift) + 1)  # para visualizar
```

Esse tópico é mais matemático — em disciplinas introdutórias costuma-se apresentar o **conceito** (o que é frequência espacial) sem entrar a fundo na matemática da FFT.

---

## 13. Segmentação de Imagens

Processo de dividir a imagem em regiões significativas (ex.: separar "objeto" de "fundo").

### Limiarização de Otsu
Escolhe automaticamente o melhor limiar (threshold) com base no histograma, maximizando a separação entre duas classes de pixels.
```python
_, otsu = cv2.threshold(cinza, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

### Segmentação baseada em bordas
Usa detecção de bordas (Canny, Sobel) seguida de conexão de contornos.

### Segmentação baseada em região (Watershed)
Trata a imagem como um "relevo topográfico" e simula o preenchimento com água a partir de marcadores para separar regiões conectadas (ex.: separar objetos que se tocam).

### Contornos
```python
contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(img, contornos, -1, (0,255,0), 2)
```

---

## 14. Compressão de Imagens

### Sem perdas (*lossless*)
Reduz o tamanho do arquivo sem perder nenhuma informação (ex.: PNG usa DEFLATE). Pode-se reconstruir a imagem original exatamente.

### Com perdas (*lossy*)
Descarta informação que o olho humano percebe pouco, obtendo arquivos muito menores (ex.: JPEG).

### Ideia geral do JPEG (bom para explicar em aula)
1. Converte RGB → YCbCr
2. Subamostra os canais de cor (Cb, Cr) — olho humano é menos sensível à cor que ao brilho
3. Divide a imagem em blocos 8×8
4. Aplica a Transformada Discreta de Cosseno (DCT) em cada bloco
5. Quantiza os coeficientes (aqui ocorre a perda de qualidade)
6. Codifica com compressão sem perdas (Huffman)

---

## 15. Panorama: Visão Computacional e Deep Learning

Bom para uma aula final "e o que vem depois?":

- **Redes Neurais Convolucionais (CNNs)**: aprendem os próprios filtros/kernels a partir de dados, em vez de usarmos filtros fixos como Sobel.
- **Classificação de imagens**: "esta imagem é um gato ou um cachorro?"
- **Detecção de objetos** (YOLO, Faster R-CNN): localizar e classificar múltiplos objetos.
- **Segmentação semântica** (U-Net): classificar cada pixel individualmente.
- Ferramentas: TensorFlow, PyTorch.

---

## 16. Ferramentas Práticas (Python)

| Biblioteca | Uso |
|---|---|
| **NumPy** | Manipulação de imagens como arrays/matrizes |
| **OpenCV** (`cv2`) | Biblioteca principal de PDI/visão computacional |
| **Pillow (PIL)** | Manipulação simples de imagens (abrir, salvar, redimensionar) |
| **Matplotlib** | Visualizar imagens e histogramas |
| **scikit-image** | Algoritmos de PDI com API mais didática |

### Setup básico para as aulas
```bash
pip install opencv-python numpy matplotlib pillow scikit-image
```

### Estrutura mínima de um script de aula
```python
import cv2
import matplotlib.pyplot as plt

img = cv2.imread("exemplo.jpg")
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # OpenCV lê em BGR, matplotlib espera RGB

plt.imshow(img_rgb)
plt.axis("off")
plt.show()
```

> **Nota didática**: o OpenCV carrega imagens no formato **BGR** (não RGB) — esse é um erro clássico de aluno iniciante ("por que minha imagem ficou azulada?"). Vale a pena destacar isso logo na primeira aula prática.

---

## 17. Sugestão de Cronograma de Aulas

Um roteiro possível para um semestre (ajuste conforme a carga horária da disciplina):

| Semana | Tema |
|---|---|
| 1 | Introdução ao PDI, aplicações, pixel, resolução |
| 2 | Modelos de cor (RGB, HSV, escala de cinza) + prática com Python |
| 3 | Aquisição, amostragem, quantização, formatos de arquivo |
| 4 | Operações pontuais: brilho, contraste, negativo, gamma |
| 5 | Histograma e equalização |
| 6 | Convolução e filtros de suavização |
| 7 | Filtros de realce e detecção de bordas (Sobel, Canny) |
| 8 | **Avaliação 1** (teoria + prática) |
| 9 | Ruído e restauração |
| 10 | Morfologia matemática |
| 11 | Transformações geométricas |
| 12 | Domínio da frequência (conceito + Fourier) |
| 13 | Segmentação de imagens (Otsu, watershed, contornos) |
| 14 | Compressão de imagens (JPEG na prática) |
| 15 | Introdução a Visão Computacional / Deep Learning |
| 16 | Apresentação de projetos finais |

---

## 18. Banco de Exercícios

Exercícios prontos, do mais simples ao mais avançado — úteis para listas ou avaliações.

1. Carregue uma imagem colorida e converta para escala de cinza usando a fórmula ponderada manualmente (sem usar `cv2.cvtColor`), comparando com o resultado do OpenCV.
2. Implemente o negativo de uma imagem sem usar nenhuma função pronta (apenas operações com arrays NumPy).
3. Plote o histograma de uma imagem escura e de uma imagem clara e explique as diferenças visuais.
4. Aplique equalização de histograma em uma imagem de raio-X (ou similar) e compare antes/depois.
5. Implemente manualmente uma convolução 3×3 com um kernel de média, sem usar `cv2.filter2D`, e valide comparando com a função pronta.
6. Compare visualmente os resultados de Sobel, Laplaciano e Canny na mesma imagem — qual detecta bordas mais "limpas"?
7. Adicione ruído sal-e-pimenta artificialmente a uma imagem e compare os filtros de média, mediana e Gaussiano na remoção do ruído.
8. Use erosão e dilatação para remover pequenos ruídos de uma imagem binarizada (ex.: imagem de um documento escaneado).
9. Rotacione uma imagem em 30°, 90° e 180°, comparando os efeitos da interpolação nas bordas.
10. Implemente um segmentador simples com limiar de Otsu e conte quantos objetos (contornos) foram encontrados.
11. **Projeto final sugerido**: pipeline completo — carregar imagem → converter para cinza → equalizar histograma → aplicar filtro Gaussiano → detectar bordas com Canny → encontrar e desenhar contornos. Apresentar cada etapa intermediária.

---

## 19. Referências

- Gonzalez, R. C.; Woods, R. E. — *Digital Image Processing* (livro-texto clássico da área)
- Documentação oficial do OpenCV: https://docs.opencv.org/
- Documentação do scikit-image: https://scikit-image.org/
- Szeliski, R. — *Computer Vision: Algorithms and Applications*

---

*Este guia foi criado como material de apoio para preparação de aulas de Processamento de Imagem. Sinta-se à vontade para adaptar a ordem dos tópicos, aprofundar a matemática onde for necessário, e complementar com exemplos visuais próprios em sala de aula.*
