"""Own compact explanations of the source equations, for forms and reports."""

PROJECT_NOTES = {
1: [
    'P1: dane znanego samolotu, literatura i trzy rzuty. Masy: pusta ≤ w locie ≤ MTOW.',
    'Podziałka 1:n = wymiar rzeczywisty [mm] / wymiar rysunku [mm]. Powiększenie wydruku = n_obecne / n_docelowe.'
],
2: [
    '(2.1–2.5) S = ∫c(y)dy; MAC = ∫c(y)²dy / S; xN = ∫c(y)xLE(y)dy / S; Λ = b²/S; λ = ck/c0.',
    'Elipsa z prostą linią połówek cięciw: S = πbc0/4; MAC = 8c0/(3π); xN = (c0 − MAC)/2.',
    '(2.6–2.9) VS = √(2mg/(ρSCzmax)); Re = VS·MAC/ν. Cxmin2 = Cxmin1·(Re1/Re2)^0,11. ΔCxRe = (Cxmin2−Cxmin1)·(1−|Cz/Cz_kryt|).',
    '(2.10–2.20) Cxp = Cxprofil + ΔCxtech + Cz²(1+δ)/(πΛ); αp = αprofil + Cz(1+τ)/(πΛ). Kąt indukowany w radianach. ΔCxtech = 0,15 Cxmin lub 0,50 Cxmin dla drewna/płótna.',
    'Poprawki Glauerta: τ = τ1τ2/0,17; δ = δ1δ2δ3/0,048. Wartości wielomianów i każdy ich składnik są podane w wynikach; idealna elipsa ma τ = δ = 0.',
    '(2.22–2.27) ΔCx = Cz²/π·[(1+δ2)/Λ2 − (1+δ1)/Λ1]; Δα = Cz/π·[(1+τ2)/Λ2 − (1+τ1)/Λ1]. ap = a∞/[1+a∞(1+τ)/(πΛ)].'
],
3: [
    '(3.1) Cxkadłub = Cf·ηk·ηMa·Somywana/Sczołowa. Gdy brak pomiaru Somywana, przybliżenie = 2,85·l·√Sczołowa.',
    'Podzespoły: pole oporu Cxj·Sj, albo siła oporu / ciśnienie dynamiczne pomiaru. Cxszk,min = Σ(CxjSj)/S.',
    '(3.3–3.6) κH′ = SH·lH/(S·MAC)·qH/q; CzH = [CmSA + Cz(xCG−xSA)]/κH′. CxH = Cxprofil,H + ΔCxszcz + CzH²/(πeHΛH).',
    '(3.8–3.10) Cxszk = Cxszk,min(1+|Cz|/ζ). Cx = (Cxp+Cxszk+CxH·SH/S)(1+Kinterf). Czsam = Czp+CzH·SH/S. To konwencja przybliżona źródła ML1.',
    '(3.11) Aproksymacja: Cx = Cx0+k·Cz². Regresja Cx(Cz²) albo odczyt nachylenia prostej. Λef = 1/(πk); e = Λef/Λ. Kontrola źródłowa e: 0,7–0,98; współczynniki pozostają nieprzycięte.',
    'Doskonałość K = Cz/Cx; funkcja energetyczna E = Cz^(3/2)/Cx. Zestawienia A/B/C służą porównaniu, bez wymuszania wartości statystycznej.'
],
4: [
    '(4.1–4.5) γopad = atan2(Cx,Cz); V = √[2mg/(ρS·√(Cz²+Cx²))]; w = V·sin(γopad). Są to równania dokładnego lotu ślizgowego.',
    '(4.6–4.12) Dla małego kąta: V ≈ √(2mg/(ρSCz)), w ≈ V·Cx/Cz. Dla Cx=Cx0+kCz²: Czopt=√(Cx0/k), Czek=√(3Cx0/k).',
    'Trzy przypadki masy/wysokości są liczone oddzielnie. Minimum kąta toru wyznacza warunki optymalne, minimum opadania — ekonomiczne.'
],
5: [
    '(5.1–5.5) J=V/(nD); CN=N/(ρn³D⁵); cecha bezśrednicowa CD=[ρV⁵/(Nn²)]^(1/5). Rozwiązanie J⁵/CN = CD⁵ daje D=V/(nJ). Nrozp=η·N.',
    'Końcówka śmigła: Ma=√[(1,2Vmax)²+(πnD)²]/a. Granica 0,9 dla metalu, 0,8 dla drewna/kompozytu; instalacyjne granice średnicy pochodzą od użytkownika.',
    '(5.6–5.8) Silnik tłokowy: N(h)=Nref·[(ρ/ρref)−k]/(1−k). Turbośmigłowy: N(h)=N0·(ρ/ρ0)^0,6. Doładowanie: odcinki regulacji oraz spadku względem wysokości krytycznych.',
    '(5.9–5.17) Śmigło stałe: Nsilnik(n)=CN(V/(nD))·ρn³D⁵. Metoda N/n=const daje n=√[(N/n)/(ρD⁵CN)]. Przy nmax moc redukuje się do mocy pochłanianej przez śmigło.',
    '(5.18–5.20) Jednoprzepływowy: T=T0·(ρ/ρ0)^0,85·(1−0,605Ma+0,725Ma²). Dwuprzepływowy: T=T0·(ρ/ρ0)^0,85·(1−KpMa). Alternatywnie tabele producenta.',
    'Mapy interpoluje się w ich zakresie. Moc/ciąg danych silnika dotyczy jednej jednostki, wynik całego napędu uwzględnia ich liczbę. n w definicjach śmigłowych ma jednostkę obr/s.'
],
6: [
    '(6.1) Obciążenie: qN=MTOW/Nmax [kg/kW], qT=MTOW/Tmax [kg/kN]. Kryteria metody mocy: odpowiednio >6 oraz >300.',
    '(6.2–6.9) Metoda mocy/ciągu: V=√(2mg/(ρSCz)), D=mg·Cx/Cz, Nniezb=D·V, w=(T−D)V/(mg), γ=asin[(T−D)/(mg)]. Przyjmuje cosγ≈1.',
    'Dokładna równowaga: Tcosε−D=Wsinγ; L+Tsinε=Wcosγ. Numerycznie: (Tcosε−D)²+(L+Tsinε)²=W². Opcjonalnie ε=α(Cz)+kąt osi ciągu względem cięciwy.',
    '(6.10–6.12) Pułapy: max w(h)=0 oraz 0,5 m/s. Czas do wysokości h: ∫dh/wmax(h). Dla liniowego spadku: t=ht/w0·ln[1/(1−h/ht)]. Czas do ht nie jest skończony.',
    '(6.13–6.28) Rezerwy odejmowane jednokrotnie. Śmigło: qpal=qe·(D·V/η)/(1000·3600) [kg/s]. Odrzut: qpal=qe·D/(10·3600) [kg/s]. T=∫dm/qpal, L=∫V·dm/qpal.',
    '(6.29–6.38) Osobne rozwiązania dla Cz=const (V maleje ze spalaniem paliwa) i V=const (Cz maleje). Dostępne wzory zamknięte dla biegunowej parabolicznej oraz całki numeryczne dla danych P3.',
    'Suplement: Ma=V/a(h), Cxściśliwy=Cxnieściśliwy/√(1−Ma²), tylko Ma<1. Korekta całego Cx jest przeliczana w punktach osiągów i całek zasięgu; nie jest stałym mnożnikiem misji.'
]}


def method_notes(project):
    return PROJECT_NOTES.get(project,[])
