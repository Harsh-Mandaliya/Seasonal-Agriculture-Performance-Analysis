# Key findings

Generated from `agriculture_data.csv` (4,000 farm records).

1. Season is the clearest yield signal: crop-adjusted median yield is 1.13 in Kharif, 0.97 in Rabi and 0.79 in Zaid (1.00 = typical for the crop). All 8 crops follow the same Kharif > Rabi > Zaid order; Zaid yields are 22-40% below Kharif depending on the crop.
2. Profitability follows the seasons: 58% of Kharif farms, 49% of Rabi farms and 36% of Zaid farms made a profit. Average cost is similar in every season and a crop's market price varies by at most 7% between seasons, so the gap comes from yield, not price.
3. Crop choice matters more than any input: Sugarcane and Chilli earn a median INR 99,569 and INR 90,245 profit per hectare, while Maize, Rice, Wheat lose money at the median (only 26-36% of those farms are profitable).
4. Drip irrigation gives the best crop-adjusted yield (1.12) and uses 32% less water per hectare than flood irrigation, which is both the most common method (1,310 farms) and the thirstiest. Rain-fed plots use the least water but have the lowest yield index (0.93).
5. Rainfall has a sweet spot: the yield index peaks in the 550-850 mm band (1.21), is lowest in the < 350 mm band (0.79) and falls back on very wet plots. Rainfall is the strongest single numeric driver (Spearman 0.24).
6. Pest risk looks *positively* related to yield when pooled (Spearman 0.14) only because pest risk rises with rainfall and humidity. After controlling for rainfall, humidity and soil moisture the partial correlation is -0.03: in this dataset pest risk has no meaningful independent effect on yield.
7. Fertiliser, pesticide volume, seed quality, soil pH and temperature show almost no relationship with crop-adjusted yield (|Spearman| < 0.05 for each; 7 of 14 candidate inputs are below that threshold), and state-level differences are small (median yield index 0.98-1.05).
8. The headline correlations in the first version of this project (water efficiency 0.92 and production 0.89 with yield) were artefacts: both columns are calculated from yield and dominated by sugarcane. They are replaced here by the crop-adjusted driver analysis.
