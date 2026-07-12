if (getQueryVariable('mode') == 'analysis')
{
    changeDate(moment().format("YYYY-MM-DD"));
    switchMode('analysis');
}
else
{
    if (isSelectableDate(inputDay))
    {
        changeDate(inputDay);
    }
    else
    {
        // Default date = today
        changeDate(moment().format("YYYY-MM-DD"));
    }
}
