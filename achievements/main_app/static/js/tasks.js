function dedupe_edu() {
    $.ajax({
    url: "/tasks/dedupe_edu",
    })
    .done (function(data, textStatus, jqXHR) {
          $('#dedupe_edu_msg').addClass('alert-success').removeClass('d-none').text(data);
    })
    .fail (function(jqXHR, textStatus, errorThrown) {
          $('#dedupe_edu_msg').addClass('alert-danger').removeClass('d-none').text(jqXHR.responseText);
    });
}