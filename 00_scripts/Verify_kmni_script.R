# source("Verify.R")
# Verification of clock-hourly and daily (8-8 UTC) rainfall accumulations.
# Output: scatter plots of radar versus rain gauge rainfall accumulations. Tables with evaluation of radar-based rainfall accumulations against rain gauges.
rm(list=ls(all=TRUE))

# Load R library for making Latex tables with metrics:
library(xtable,lib.loc="/usr/people/overeem/Rlibraries/")
# Load R libraries for making scatter density plots:
library(hexbin,lib.loc="/usr/people/overeem/Rlibraries")
library(lattice,lib.loc="/usr/people/overeem/Rlibraries")

# Function that returns Mean Absolute Error
mae <- function(error)
{
    mean(abs(error))
}

# Settings for scatter density plot (both clock-hourly & daily):
colorkey <- TRUE    # If FALSE no legend is plotted, if TRUE legend is plotted.
if (colorkey==FALSE)
{
   cex.lab <- 1.5
   cex.title <- 2
   ps <- 30
   xlab.text.cex <- 2.5
   ylab.text.cex <- 2.5
   main.text.cex <- 1.9
   cex.text <- 1.5
   cex.text2 <- 1.7   
   cex.axis <- 2.5   
   #maxcnt <- 3200
}
if (colorkey==TRUE)
{
   cex.lab <- 1.5
   cex.title <- 1.5
   ps <- 25
   xlab.text.cex <- 2.0
   ylab.text.cex <- 2.0
   main.text.cex <- 1.2
   cex.text <- 1.3
   cex.text2 <- 1.3   
   cex.axis <- 1.8
   #maxcnt <- 3200         
}


# VERIFICATION of clock-hourly rainfall.
########################################
NameFigScat <- c("figures/LOOS_01H_ADC_NoGauge.pdf",
"figures/LOOS_01H_ADC_KNMIAWS.pdf")
NameFigScatDens <- c("figures/ScatterDensityLOOS_01H_ADC_NoGauge.pdf",
"figures/ScatterDensityLOOS_01H_ADC_KNMIAWS.pdf")
NameTable <- c("tables/Table_LOOS_01H_ADC_NoGauge.dat",
"tables/Table_LOOS_01H_ADC_KNMIAWS.dat")
InputFile <- c("LOOS_RAD_NL25_RAC_01H_ADC_KNMIAWS.dat",
"LOOS_RAD_NL25_RAC_01H_ADC_KNMIAWS.dat")
MainText <- c("Radarcorrecties",
"Radarcorrecties + KNMI AWS regenm.")
Adjusted <- c("FALSE","TRUE")   # If TRUE use the gauge-adjusted radar values. 
# If FALSE use the radar values from the input dataset used in the program which computes leave-one-out-statistics (LOOS).
cex.main <- c(2.5,1.9)


for (FileNr in 1:length(InputFile))
{

   # Rainfall threshold in mm, i.e., everything as of this value is taken into account:
   threshold <- 0
   pdf(NameFigScat[FileNr],family="Times") 
   par(ps=11)
   par(pty="s")
   par(mar=c(4.5,5.7,2.5,1.5))
   par(mfrow=c(1,1))
   u <- read.table(InputFile[FileNr],sep=",")
   cond <- which(u[,9]>=threshold)
   if (Adjusted[FileNr]=="FALSE")
   {
        Radar <- u[cond,7]
   }
   if (Adjusted[FileNr]=="TRUE")
   {
        Radar <- u[cond,8]   
   }   
   if (Adjusted[FileNr]!="TRUE" & Adjusted[FileNr]!="FALSE")
   {
        print("Adjusted (TRUE) or not adjusted (FALSE) is not specified! Program is terminated.")
        stop()
   }
   Gauge <- u[cond,9]
   print(paste0("Uursom: ",max(max(Radar),max(Gauge))))
   R_total <- Gauge
   R_total_est <- Radar
   Residuals <- R_total_est - R_total
   gauge_mean <- mean(R_total)
   rad_mean <- mean(R_total_est)
   CV <- sd(Residuals)/mean(R_total)
   corSQR <- cor(R_total,R_total_est)^2 
   BiasTotal <- mean(Residuals)
   MeanRefTotal <- mean(R_total)
   # Compute relative bias in the mean (%).
   RelBiasTotal <- BiasTotal/MeanRefTotal * 100

   gauge_mean <- formatC(gauge_mean, format="f", digits=2)
   rad_mean <- formatC(rad_mean, format="f", digits=2)
   CV <- formatC(CV, format="f", digits=2)
   corSQR <- formatC(corSQR, format="f", digits=2)
   RelBias <- formatC(RelBiasTotal, format="f", digits=1)


   #####################
   # Make scatter plot:#
   #####################
   plot(R_total,R_total_est,xlim=c(0,46),ylim=c(0,46),xlab=expression("Uursom regenmeter (mm)"),ylab=expression("Uursom radar (mm)"), pch=16,mgp=c(3.3,1,0),main=MainText[FileNr],col="gray55",cex.axis=3,cex.lab=3,cex.main=cex.main[FileNr]*0.8)
   curve(1*x,add=TRUE,col="black",lwd=2)
   text(8.62,45.4,substitute(bar(italic(R))[regenm.] == gauge_mean*" mm",list(gauge_mean=gauge_mean)),col=c("black"),cex=2.0)
   text(9.51,42.8,substitute("Rel. bias" == RelBias*" %",list(RelBias=RelBias)),col=c("black"),cex=2.0)
   text(9.82,40.3,substitute(italic("CV") == CV*"",list(CV=CV)),col=c("black"),cex=2.0) 
   text(9.82,37.76,substitute(rho^2 == corSQR,list(corSQR=corSQR)),col=c("black"),cex=2.0)	
   text(9.82,35.23,substitute(italic("n") == n*"",list(n=length(R_total))),col=c("black"),cex=2.0) 
   dev.off()


   #############################
   # Make scatter density plot:#
   #############################
   pdf(NameFigScatDens[FileNr],family="Times")
   par(ps=ps)
   par(pty="s")
   spam <- range(c(min(R_total),max(R_total),min(R_total_est),max(R_total_est)))
   fig<-hexbinplot(R_total_est ~ R_total, aspect = 1, cex.lab=cex.lab, cex.title=cex.title, ylab=expression("Uursom radar (mm)"),main=MainText[FileNr],xlab=expression("Uursom regenmeter (mm)"), xlim=c(-2,50), ylim=c(-2,50), colorkey=colorkey, style="colorscale",xbnds=c(floor(spam[1]),ceiling(spam[2])),xbins=ceiling(spam[2])/1,scales = list(x = list(cex=cex.axis),y = list(cex=cex.axis)),par.settings = list(par.xlab.text=list(cex=xlab.text.cex),par.ylab.text=list(cex=ylab.text.cex),par.main.text=list(cex=main.text.cex,y=0.1)),mincnt=1,#maxcnt=maxcnt,
trans=log, inv = function(R_total) exp(R_total), colorcut = seq(0, 1, length = 7), colramp = function(n) plinrain(n, beg=160, end=20), panel=function(x, y, ...){
                  panel.hexbinplot(x,y,...)
                  panel.curve(1*x,add=TRUE,col="gray55",lwd=2)	       
	          panel.text(32.5,0,"Augustus 2017 - juli 2018",col=c("black"),cex=cex.text2)
                  panel.text(9.12,47.4,substitute(bar(italic(R))[regenm.] == gauge_mean*" mm",list(gauge_mean=gauge_mean)),col=c("black"),cex=cex.text)
                  panel.text(10.01,44.8,substitute("Rel. bias" == RelBias*" %",list(RelBias=RelBias)),col=c("black"),cex=cex.text)
                  panel.text(10.32,42.3,substitute(italic("CV") == CV*"",list(CV=CV)),col=c("black"),cex=cex.text) 
                  panel.text(10.32,39.76,substitute(rho^2 == corSQR,list(corSQR=corSQR)),col=c("black"),cex=cex.text)	
                  panel.text(10.32,37.23,substitute(italic("n") == n*"",list(n=length(R_total))),col=c("black"),cex=cex.text)    
                  #panel.text(9.82,31.7,substitute(italic(R)[regenm.] > threshold*" mm",list(threshold=threshold)),col=c("black"),cex=cex.tex)                   
              })
   print(fig)
   dev.off()
   
   
   #############################   
   # Compute metrics for table:#
   #############################
   BiasTotal <- ResStdDevTotal <- CorTotal <- MeanRefTotal <- RelBiasTotal <- MAE <- n <- c(NA)
   Gauge <- u[,9]
   if (Adjusted[FileNr]=="FALSE")
   {
        Radar <- u[,7]
   }
   if (Adjusted[FileNr]=="TRUE")
   {
        Radar <- u[,8]   
   }    
   
   # Calculate residuals.
    Residuals <- Radar - Gauge
    BiasTotal[1] <- mean(Residuals)
    ResStdDevTotal[1] <- sd(Residuals)
    CorTotal[1] <- cor(Radar,Gauge)
    MAE[1] <- mae(Residuals)
    MeanRefTotal[1] <- mean(Gauge)
    # Compute relative bias in the mean (%).
    RelBiasTotal[1] <- BiasTotal[1]/MeanRefTotal[1] * 100
    n[1] <- length(Residuals)

    # Threshold in mm:
    threshold <- 0.1
    cond <- which(Radar> threshold | Gauge > threshold)
    BiasTotal[2] <- mean(Residuals[cond])
    ResStdDevTotal[2] <- sd(Residuals[cond])
    CorTotal[2] <- cor(Radar[cond],Gauge[cond])
    MAE[2] <- mae(Residuals[cond])
    MeanRefTotal[2] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%).
    RelBiasTotal[2] <- BiasTotal[2]/MeanRefTotal[2] * 100
    n[2] <- length(Residuals[cond])    

    # Threshold in mm:
    threshold <- 5
    cond <- which(Radar> threshold | Gauge > threshold)
    BiasTotal[3] <- mean(Residuals[cond])
    ResStdDevTotal[3] <- sd(Residuals[cond])
    CorTotal[3] <- cor(Radar[cond],Gauge[cond])
    MAE[3] <- mae(Residuals[cond])
    MeanRefTotal[3] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%).
    RelBiasTotal[3] <- BiasTotal[3]/MeanRefTotal[3] * 100
    n[3] <- length(Residuals[cond])    

    threshold <- 10
    cond <- which(Radar> threshold | Gauge > threshold)
    BiasTotal[4] <- mean(Residuals[cond])
    ResStdDevTotal[4] <- sd(Residuals[cond])
    CorTotal[4] <- cor(Radar[cond],Gauge[cond])
    MAE[4] <- mae(Residuals[cond])
    MeanRefTotal[4] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%).
    RelBiasTotal[4] <- BiasTotal[4]/MeanRefTotal[4] * 100
    n[4] <- length(Residuals[cond])        

    # Threshold in mm (gauge = 0 mm!):
    threshold <- 0
    cond <- which(Gauge==threshold)
    BiasTotal[5] <- mean(Residuals[cond])
    ResStdDevTotal[5] <- sd(Residuals[cond])
    #CorTotal[5] <- cor(Radar[cond],Gauge[cond])
    CorTotal[5] <- NA
    MAE[5] <- mae(Residuals[cond])
    MeanRefTotal[5] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%). Here, we keep the bias in the mean (mm)!
    RelBiasTotal[5] <- BiasTotal[5]
    n[5] <- length(Residuals[cond])        

    Threshold <- c(NA, 0.1, 5, 10, 0)
    dataf <- data.frame(cbind(Threshold,MeanRefTotal,RelBiasTotal,ResStdDevTotal,CorTotal,MAE,n))
    names(dataf) <- c("Threshold value (mm)","Mean hourly rainfall","Rel. bias (%)","Res. std. dev. (mm)","Correlation","MAE (mm)","n")
    tab <- xtable(dataf,caption="Validation of radar hourly rainfall depths against automatic rain gauges over 3 August 2017 08:00 UTC - 31 July 2018 08:00 UTC. The mean hourly rainfall is based on the automatic rain gauge data.",digits=c(0,1,2,1,2,2,2,0))
    print(tab,file=NameTable[FileNr],include.rownames=FALSE)   
    
}




# VERIFICATION of daily rainfall.
#################################
NameFigScat <- c("figures/LOOS_24H_8UT_ADC_NoGauge_vs_KNMISTN.pdf",
"figures/LOOS_24H_8UT_ADC_KNMIAWS_vs_KNMISTN.pdf")
NameFigScatDens <- c("figures/ScatterDensityLOOS_24H_8UT_ADC_NoGauge_vs_KNMISTN.pdf",
"figures/ScatterDensityLOOS_24H_8UT_ADC_KNMIAWS_vs_KNMISTN.pdf")
NameTable <- c("tables/Table_LOOS_24H_8UT_ADC_NoGauge_vs_KNMISTN.dat",
"tables/Table_LOOS_24H_8UT_ADC_KNMIAWS_vs_KNMISTN.dat")
InputFile <- c("LOOS_RAD_NL25_RAU_24H_8UT_ADC.dat",
"LOOS_RAD_NL25_RAC_24H_8UT_ADC_KNMIAWS.dat")
MainText <- c("Radarcorrecties",
"Radarcorrecties + KNMI AWS regenm.")
Adjusted <- c("FALSE","FALSE")   # If TRUE use the gauge-adjusted radar values.  
# If FALSE use the radar values from the input dataset used in the program which computes leave-one-out-statistics (LOOS).
cex.main <- c(2.5,2.5)


for (FileNr in 1:length(InputFile))
{

   # Rainfall threshold in mm, i.e., everything as of this value is taken into account:
   threshold <- 1
   pdf(NameFigScat[FileNr],family="Times") 
   par(ps=11)
   par(pty="s")
   par(mar=c(4.5,5.7,2.5,1.5))
   par(mfrow=c(1,1))
   u <- read.table(InputFile[FileNr],sep=",")
   #cond <- which(u[,9]>=threshold)
   cond <- which(u[,9]>threshold)
   if (Adjusted[FileNr]=="FALSE")
   {
        Radar <- u[cond,7]
   }
   if (Adjusted[FileNr]=="TRUE")
   {
        Radar <- u[cond,8]   
   }   
   if (Adjusted[FileNr]!="TRUE" & Adjusted[FileNr]!="FALSE")
   {
        print("Adjusted (TRUE) or not adjusted (FALSE) is not specified! Program is terminated.")
        stop()
   }
   Gauge <- u[cond,9]
   print(paste0("Dagsom: ",max(max(Radar),max(Gauge))))
   R_total <- Gauge
   R_total_est <- Radar
   Residuals <- R_total_est - R_total
   gauge_mean <- mean(R_total)
   rad_mean <- mean(R_total_est)
   CV <- sd(Residuals)/mean(R_total)
   corSQR <- cor(R_total,R_total_est)^2 
   BiasTotal <- mean(Residuals)
   MeanRefTotal <- mean(R_total)
   # Compute relative bias in the mean (%).
   RelBiasTotal <- BiasTotal/MeanRefTotal * 100

   gauge_mean <- formatC(gauge_mean, format="f", digits=2)
   rad_mean <- formatC(rad_mean, format="f", digits=2)
   CV <- formatC(CV, format="f", digits=2)
   corSQR <- formatC(corSQR, format="f", digits=2)
   RelBias <- formatC(RelBiasTotal, format="f", digits=1)


   #####################
   # Make scatter plot:#
   #####################
   plot(R_total,R_total_est,xlim=c(0,150),ylim=c(0,150),xlab=expression("Dagsom regenmeter (mm)"),ylab=expression("Dagsom radar (mm)"), pch=16,mgp=c(3.3,1,0),main=MainText[FileNr],col="gray55",cex.axis=3,cex.lab=3,cex.main=cex.main[FileNr]*0.8)
   curve(1*x,add=TRUE,col="black",lwd=2)
   text(32.73,148,substitute(bar(italic(R))[regenm.] == gauge_mean*" mm",list(gauge_mean=gauge_mean)),col=c("black"),cex=2.0)
   text(31.7,139.33,substitute("Rel. bias" == RelBias*" %",list(RelBias=RelBias)),col=c("black"),cex=2.0)
   text(32.73,131,substitute(italic("CV") == CV*"",list(CV=CV)),col=c("black"),cex=2.0) 
   text(32.73,122.53,substitute(rho^2 == corSQR,list(corSQR=corSQR)),col=c("black"),cex=2.0)	
   text(32.73,114.1,substitute(italic("n") == n*"",list(n=length(R_total))),col=c("black"),cex=2.0)    
   text(32.73,105.67,substitute(italic(R)[regenm.] > threshold*" mm",list(threshold=threshold)),col=c("black"),cex=2.0)      
   dev.off()
   
   
   #############################
   # Make scatter density plot:#
   #############################
   pdf(NameFigScatDens[FileNr],family="Times")
   par(ps=ps)
   par(pty="s")
   spam <- range(c(min(R_total),max(R_total),min(R_total_est),max(R_total_est)))
   fig<-hexbinplot(R_total_est ~ R_total, aspect = 1, cex.lab=cex.lab, cex.title=cex.title, ylab=expression("Dagsom radar (mm)"),main=MainText[FileNr],xlab=expression("Dagsom regenmeter (mm)"), xlim=c(-4,154), ylim=c(-4,154), colorkey=colorkey, style="colorscale",xbnds=c(floor(spam[1]),ceiling(spam[2])),xbins=ceiling(spam[2])/1,scales = list(x = list(cex=cex.axis),y = list(cex=cex.axis)),par.settings = list(par.xlab.text=list(cex=xlab.text.cex),par.ylab.text=list(cex=ylab.text.cex),par.main.text=list(cex=main.text.cex,y=0.1)),mincnt=1,#maxcnt=maxcnt,
trans=log, inv = function(R_total) exp(R_total), colorcut = seq(0, 1, length = 7), colramp = function(n) plinrain(n, beg=160, end=20), panel=function(x, y, ...){
                  panel.hexbinplot(x,y,...)
                  panel.curve(1*x,add=TRUE,col="gray55",lwd=2)	       
	          panel.text(97,3,"Augustus 2017 - juli 2018",col=c("black"),cex=cex.text2)
                  panel.text(32.73,148,substitute(bar(italic(R))[regenm.] == gauge_mean*" mm",list(gauge_mean=gauge_mean)),col=c("black"),cex=cex.text)
                  panel.text(31.7,139.33,substitute("Rel. bias" == RelBias*" %",list(RelBias=RelBias)),col=c("black"),cex=cex.text)
                  panel.text(32.73,131,substitute(italic("CV") == CV*"",list(CV=CV)),col=c("black"),cex=cex.text) 
                  panel.text(32.73,122.53,substitute(rho^2 == corSQR,list(corSQR=corSQR)),col=c("black"),cex=cex.text)	
                  panel.text(32.73,114.1,substitute(italic("n") == n*"",list(n=length(R_total))),col=c("black"),cex=cex.text)    
                  panel.text(32.73,105.67,substitute(italic(R)[regenm.] > threshold*" mm",list(threshold=threshold)),col=c("black"),cex=cex.text)                   
              })
   print(fig)
   dev.off()

   
   #############################   
   # Compute metrics for table:#
   #############################
   BiasTotal <- ResStdDevTotal <- CorTotal <- MeanRefTotal <- RelBiasTotal <- MAE <- n <- c(NA)
   Gauge <- u[,9]
   if (Adjusted[FileNr]=="FALSE")
   {
        Radar <- u[,7]
   }
   if (Adjusted[FileNr]=="TRUE")
   {
        Radar <- u[,8]   
   }    
   
   # Calculate residuals.
    Residuals <- Radar - Gauge
    BiasTotal[1] <- mean(Residuals)
    ResStdDevTotal[1] <- sd(Residuals)
    CorTotal[1] <- cor(Radar,Gauge)
    MAE[1] <- mae(Residuals)
    MeanRefTotal[1] <- mean(Gauge)
    # Compute relative bias in the mean (%).
    RelBiasTotal[1] <- BiasTotal[1]/MeanRefTotal[1] * 100
    n[1] <- length(Residuals)

    # Threshold in mm:
    threshold <- 0.1
    cond <- which(Radar> threshold | Gauge > threshold)
    BiasTotal[2] <- mean(Residuals[cond])
    ResStdDevTotal[2] <- sd(Residuals[cond])
    CorTotal[2] <- cor(Radar[cond],Gauge[cond])
    MAE[2] <- mae(Residuals[cond])
    MeanRefTotal[2] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%).
    RelBiasTotal[2] <- BiasTotal[2]/MeanRefTotal[2] * 100
    n[2] <- length(Residuals[cond])    

    # Threshold in mm:
    threshold <- 10
    cond <- which(Radar> threshold | Gauge > threshold)
    BiasTotal[3] <- mean(Residuals[cond])
    ResStdDevTotal[3] <- sd(Residuals[cond])
    CorTotal[3] <- cor(Radar[cond],Gauge[cond])
    MAE[3] <- mae(Residuals[cond])
    MeanRefTotal[3] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%).
    RelBiasTotal[3] <- BiasTotal[3]/MeanRefTotal[3] * 100
    n[3] <- length(Residuals[cond])    

    threshold <- 20
    cond <- which(Radar> threshold | Gauge > threshold)
    BiasTotal[4] <- mean(Residuals[cond])
    ResStdDevTotal[4] <- sd(Residuals[cond])
    CorTotal[4] <- cor(Radar[cond],Gauge[cond])
    MAE[4] <- mae(Residuals[cond])
    MeanRefTotal[4] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%).
    RelBiasTotal[4] <- BiasTotal[4]/MeanRefTotal[4] * 100
    n[4] <- length(Residuals[cond])        

    # Threshold in mm (gauge = 0 mm!):
    threshold <- 0
    cond <- which(Gauge==threshold)
    BiasTotal[5] <- mean(Residuals[cond])
    ResStdDevTotal[5] <- sd(Residuals[cond])
    #CorTotal[5] <- cor(Radar[cond],Gauge[cond])
    CorTotal[5] <- NA
    MAE[5] <- mae(Residuals[cond])
    MeanRefTotal[5] <- mean(Gauge[cond])
    # Compute relative bias in the mean (%). Here, we keep the bias in the mean (mm)!
    RelBiasTotal[5] <- BiasTotal[5]
    n[5] <- length(Residuals[cond])        

    Threshold <- c(NA, 0.1, 10, 20, 0)
    dataf <- data.frame(cbind(Threshold,MeanRefTotal,RelBiasTotal,ResStdDevTotal,CorTotal,MAE,n))
    names(dataf) <- c("Threshold value (mm)","Mean daily rainfall","Rel. bias (%)","Res. std. dev. (mm)","Correlation","MAE (mm)","n")
    tab <- xtable(dataf,caption="Validation of radar daily rainfall depths against the manual rain gauge network over 3 August 2017 08:00 UTC - 31 July 2018 08:00 UTC. The mean daily rainfall is based on the manual rain gauge data.",digits=c(0,1,2,1,2,2,2,0))
    print(tab,file=NameTable[FileNr],include.rownames=FALSE)   

}



