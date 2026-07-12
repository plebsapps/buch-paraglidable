function applyColorBlind(className)
{
    if (g_arrColorBlindAngles[colorBlindValue%g_arrColorBlindAngles.length] == 0)
    {
        $("."+className).css('filter', '');
    }
    else
    {
        $("."+className).css('filter', 'hue-rotate('+ (g_arrColorBlindAngles[colorBlindValue%g_arrColorBlindAngles.length]) +'deg)');
    }
}

function updateColorBlindLinkText()
{
    var arrStrMode = ["aus", "1/2", "2/2"];
    $("#colorBlindModeStrValLink").html(arrStrMode[colorBlindValue%arrStrMode.length]);
}

function updateColorBlind()
{
    applyColorBlind("colorMap");
    applyColorBlind("keywordVal");
    updateColorBlindLinkText();
    downloadSpotsPredictions();
}

function switchColorBlind()
{
    colorBlindValue++;
    setCookie("colorBlindValue", colorBlindValue.toString());

    updateColorBlind();
}


var cookieColorBlindValue = getCookie("colorBlindValue");
if (cookieColorBlindValue != "")
{
    colorBlindValue = parseInt(cookieColorBlindValue);
    updateColorBlind();
}
else
{
    updateColorBlindLinkText();
}
