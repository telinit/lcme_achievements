function filter_changed() {
    let dep_id = $('#filter_dep').val()
    let fio = $('#fio_filter').val()

    $('.student_list .item').each(
        (i, e) => {
            let dep_ok = dep_id == "" || $(e).attr('x-dep-id') == dep_id
            let fio_ok = $(e, '.fio').text().toLowerCase().includes( fio.toLowerCase() )

            if (dep_ok && fio_ok) {
                $(e).removeClass('d-none')
            } else {
                $(e).addClass('d-none')
            }
        }
    )
}