var selected_type = undefined;
var selected_date = undefined;

function select_doc_type(type, summer_date, sid) {
    selected_type = type;
    selected_date = summer_date;

    switch (selected_type) {
        case 'everything':
            $('#download_pdf').attr('href', `/print/student/${sid}/pdf`)
            $('#download_odt').attr('href', `/print/student/${sid}/odt`)
            break;
        case 'summer':
            $('#download_pdf').attr('href', `/print/student_summer/${sid}/${summer_date}/pdf`)
            $('#download_odt').attr('href', `/print/student_summer/${sid}/${summer_date}/odt`)
            break;
        default:
            break;
    }

    $('#download').removeClass('d-none')
}