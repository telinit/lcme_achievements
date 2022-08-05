function dedupe_edu() {
    $('#dedupe_edu_spinner').removeClass('d-none')
    $.ajax({
    url: "/tasks/dedupe_edu",
    })
    .done (function(data, textStatus, jqXHR) {
          $('#dedupe_edu_msg').addClass('alert-success').removeClass('d-none').text(data);
    })
    .fail (function(jqXHR, textStatus, errorThrown) {
          $('#dedupe_edu_msg').addClass('alert-danger').removeClass('d-none').text(jqXHR.responseText);
    })
    .always(function() {
        $('#dedupe_edu_spinner').addClass('d-none')
    });
}

function check_names() {
    $('#check_names_spinner').removeClass('d-none')
    $.ajax({
    url: "/tasks/check_names",
    })
    .done (function(data, textStatus, jqXHR) {
          $('#modal_dialog .modal-title').html('Результаты');
          $('#modal_dialog .modal-body').html(data);
          $('#modal_dialog').modal('show');
    })
    .fail (function(jqXHR, textStatus, errorThrown) {
          $('#check_names_msg').addClass('alert-danger').removeClass('d-none').text(jqXHR.responseText);
    })
    .always(function() {
        $('#check_names_spinner').addClass('d-none')
    });
}

function find_similar() {
    let t = $("#find_similar_obj_type").val()
    let l = $("#find_similar_limit").val()
    let m = $("#find_similar_method").val()
    $('#find_similar_spinner').removeClass('d-none')
    $.ajax({
    url: `/tasks/find_similar_objects/${t}/${m}/${l}`,
    })
    .done (function(data, textStatus, jqXHR) {
            // .addClass('alert-success')
          // $('#find_similar_msg').removeClass('d-none').html(data);
          $('#modal_dialog .modal-title').html('Результаты');
          $('#modal_dialog .modal-body').html(data);
          $('#modal_dialog').modal('show');
    })
    .fail (function(jqXHR, textStatus, errorThrown) {
          $('#find_similar_msg').addClass('alert-danger').removeClass('d-none').text(jqXHR.responseText);
    })
    .always(function() {
        $('#find_similar_spinner').addClass('d-none')
    });
}