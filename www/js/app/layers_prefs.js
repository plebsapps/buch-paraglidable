    function updateShowHideColors()
    {
        if (showHideColorsVal == 1)
        {
            applyShowHideMapColors(true);
            $("#checkboxShowHideMapColors").css("background-image", "url('imgs/icons/check.svg')");
        }
        else
        {
            applyShowHideMapColors(false);
            $("#checkboxShowHideMapColors").css("background-image", "none");
        }
    }

    function updateShowHideSpots()
    {
        if (showHideSpotsVal == 1)
        {
            applyShowHideSpots(true);
            $("#checkboxShowHideSpots").css("background-image", "url('imgs/icons/check.svg')");
        }
        else
        {
            applyShowHideSpots(false);
            $("#checkboxShowHideSpots").css("background-image", "none");
        }
    }

    function showHideColors() {
        showHideColorsVal = (++showHideColorsVal)%2;
        setCookie("showHideColorsVal", showHideColorsVal.toString());
        updateShowHideColors();
    }

    function showHideSpots()
    {
        showHideSpotsVal = (++showHideSpotsVal)%2;
        setCookie("showHideSpotsVal", showHideSpotsVal.toString());
        updateShowHideSpots();
    }

    var cookieShowHideColorsVal = getCookie("showHideColorsVal");
    if (cookieShowHideColorsVal != "")
    {
        showHideColorsVal = parseInt(cookieShowHideColorsVal);
        updateShowHideColors();
    }
    else
    {
        $("#checkboxShowHideMapColors").css("background-image", "url('imgs/icons/check.svg')");
    }


    var cookieShowHideSpotsVal = getCookie("showHideSpotsVal");
    if (cookieShowHideSpotsVal != "")
    {
        showHideSpotsVal = parseInt(cookieShowHideSpotsVal);
        updateShowHideSpots();
    }
    else
    {
        $("#checkboxShowHideSpots").css("background-image", "url('imgs/icons/check.svg')");
    }


    function switchLayersVisibility(layer)
    {
        if (layer==0)
        {
            showHideColors();
        }
        else if (layer==1)
        {
            showHideSpots();
        }
    }
